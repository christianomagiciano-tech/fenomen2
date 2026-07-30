from __future__ import annotations

import pytest

from backend.contracts.events.base import Event
from backend.kernel.event_bus.bus import EventBus


class _SampleEvent(Event):
    payload: str


class _OtherEvent(Event):
    pass


async def test_subscriber_receives_published_event() -> None:
    bus = EventBus()
    received: list[_SampleEvent] = []

    async def handler(event: _SampleEvent) -> None:
        received.append(event)

    bus.subscribe(_SampleEvent, handler)
    await bus.publish(_SampleEvent(source="test", payload="hello"))

    assert len(received) == 1
    assert received[0].payload == "hello"


async def test_multiple_subscribers_all_receive_event() -> None:
    bus = EventBus()
    calls: list[str] = []

    async def handler_a(event: _SampleEvent) -> None:
        calls.append("a")

    async def handler_b(event: _SampleEvent) -> None:
        calls.append("b")

    bus.subscribe(_SampleEvent, handler_a)
    bus.subscribe(_SampleEvent, handler_b)
    await bus.publish(_SampleEvent(source="test", payload="x"))

    assert sorted(calls) == ["a", "b"]


async def test_subscriber_only_receives_its_own_event_type() -> None:
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: _SampleEvent) -> None:
        received.append(event)

    bus.subscribe(_SampleEvent, handler)
    await bus.publish(_OtherEvent(source="test"))

    assert received == []


async def test_unsubscribe_stops_further_delivery() -> None:
    bus = EventBus()
    received: list[_SampleEvent] = []

    async def handler(event: _SampleEvent) -> None:
        received.append(event)

    bus.subscribe(_SampleEvent, handler)
    bus.unsubscribe(_SampleEvent, handler)
    await bus.publish(_SampleEvent(source="test", payload="x"))

    assert received == []


async def test_unsubscribe_unknown_handler_is_a_no_op() -> None:
    bus = EventBus()

    async def handler(event: _SampleEvent) -> None:
        pass

    # Never subscribed — must not raise.
    bus.unsubscribe(_SampleEvent, handler)


async def test_publish_with_no_subscribers_does_not_raise() -> None:
    bus = EventBus()
    await bus.publish(_SampleEvent(source="test", payload="x"))


async def test_failing_handler_does_not_prevent_other_handlers_from_running() -> None:
    bus = EventBus()
    calls: list[str] = []

    async def failing_handler(event: _SampleEvent) -> None:
        calls.append("failing")
        raise RuntimeError("boom")

    async def healthy_handler(event: _SampleEvent) -> None:
        calls.append("healthy")

    bus.subscribe(_SampleEvent, failing_handler)
    bus.subscribe(_SampleEvent, healthy_handler)

    # Must not raise, despite one handler failing.
    await bus.publish(_SampleEvent(source="test", payload="x"))

    assert sorted(calls) == ["failing", "healthy"]


async def test_subscriber_count_reflects_subscriptions() -> None:
    bus = EventBus()

    async def handler(event: _SampleEvent) -> None:
        pass

    assert bus.subscriber_count(_SampleEvent) == 0
    bus.subscribe(_SampleEvent, handler)
    assert bus.subscriber_count(_SampleEvent) == 1
    bus.unsubscribe(_SampleEvent, handler)
    assert bus.subscriber_count(_SampleEvent) == 0


def test_event_is_immutable() -> None:
    event = _SampleEvent(source="test", payload="x")
    with pytest.raises(Exception):
        event.payload = "changed"  # type: ignore[misc]
