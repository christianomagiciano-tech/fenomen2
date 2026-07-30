"""
In-process, asyncio-native publish/subscribe event bus.

This is the sole communication path between modules — see
`docs/architecture/decisions/0001-microkernel-event-bus.md` for why.

Phase 0 implementation notes
-----------------------------
This implementation dispatches events directly to subscriber coroutines
within the publishing task (fanned out with `asyncio.gather`). It is
intentionally the simplest thing that satisfies the public interface below.
When multi-node support (Phase 8) requires a networked backend (e.g. Redis
Pub/Sub or NATS), that backend will be implemented as another class
satisfying the same `publish` / `subscribe` / `unsubscribe` shape. No
module code will need to change — only the object the composition root
(`app.py`) constructs.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, TypeVar

from backend.contracts.events.base import Event

EventT = TypeVar("EventT", bound=Event)
EventHandler = Callable[[EventT], Awaitable[None]]

_logger = logging.getLogger("fenomen.kernel.event_bus")


class EventBus:
    """A typed, in-process, asyncio publish/subscribe event bus."""

    def __init__(self) -> None:
        # Keyed by the *exact* event class. Subclasses of a subscribed
        # event type are NOT automatically delivered — event identity is
        # explicit, not based on inheritance, to avoid surprising fan-out.
        self._subscribers: DefaultDict[type[Event], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[EventT], handler: EventHandler) -> None:
        """
        Register `handler` to be called with every future instance of
        `event_type` published on this bus. `handler` must be an async
        callable accepting a single argument of that event type.
        """
        self._subscribers[event_type].append(handler)
        _logger.debug(
            "Subscribed %s to %s",
            getattr(handler, "__qualname__", repr(handler)),
            event_type.__name__,
        )

    def unsubscribe(self, event_type: type[EventT], handler: EventHandler) -> None:
        """
        Remove a previously registered handler. Safe to call even if the
        handler is not currently subscribed (a no-op in that case) — this
        keeps module `stop()` implementations simple, since they don't
        need to track exactly what they subscribed during `initialize()`.
        """
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)
            _logger.debug(
                "Unsubscribed %s from %s",
                getattr(handler, "__qualname__", repr(handler)),
                event_type.__name__,
            )

    async def publish(self, event: Event) -> None:
        """
        Deliver `event` to every handler subscribed to its exact type.

        Handlers run concurrently. If a handler raises, the exception is
        logged and isolated — it does not prevent delivery to other
        handlers and does not propagate to the publisher. A misbehaving
        subscriber must never be able to break the module that published
        the event; the two are, by design, unaware of each other.
        """
        handlers = list(self._subscribers.get(type(event), ()))
        _logger.debug(
            "Publishing %s (event_id=%s, source=%s) to %d subscriber(s)",
            type(event).__name__,
            event.event_id,
            event.source,
            len(handlers),
        )
        if not handlers:
            return

        results = await asyncio.gather(
            *(self._invoke(handler, event) for handler in handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                _logger.error(
                    "Event handler raised while handling %s",
                    type(event).__name__,
                    exc_info=result,
                )

    @staticmethod
    async def _invoke(handler: EventHandler, event: Event) -> None:
        await handler(event)

    def subscriber_count(self, event_type: type[Event]) -> int:
        """Number of handlers currently subscribed to `event_type`. Mainly for tests/diagnostics."""
        return len(self._subscribers.get(event_type, ()))
