"""
The module contract.

Every capability in Fenomen 2 (voice recognition, memory, reasoning, an
individual agent, ...) is a "module": a class implementing :class:`Module`.
Modules are the unit the kernel knows how to load, initialize, start, and
stop. A module must never import another module's internals — it may only
depend on `backend.contracts` and on the :class:`ModuleContext` it is
handed at initialization time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    import logging

    from backend.kernel.config.manager import ConfigManager
    from backend.kernel.event_bus.bus import EventBus


class ModuleState(str, Enum):
    """
    Lifecycle states a module can be in.

    Valid transitions:
        UNLOADED -> INITIALIZED -> STARTED -> STOPPED
    `FAILED` is reachable from any state if a lifecycle method raises.
    A module in STOPPED state may be re-initialized (e.g. plugin reload)
    in a future phase; Phase 0 does not require or forbid this, it simply
    is not exercised yet.
    """

    UNLOADED = "unloaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    FAILED = "failed"


class ModuleMetadata(BaseModel):
    """Static, descriptive information about a module."""

    name: str
    version: str
    description: str = ""


@dataclass(frozen=True)
class ModuleContext:
    """
    Everything the kernel hands a module at initialization time.

    This is the *only* way a module reaches the rest of the system —
    there is no global/singleton access to the event bus, config, or
    logging. A module that isn't given a `ModuleContext` cannot talk to
    anything, which makes modules straightforward to unit test in
    isolation (construct a fake/real context, no monkeypatching required).
    """

    event_bus: "EventBus"
    config: "ConfigManager"
    logger: "logging.Logger"


class Module(ABC):
    """Base class every Fenomen 2 module must implement."""

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """Static metadata identifying this module."""

    @abstractmethod
    async def initialize(self, context: ModuleContext) -> None:
        """
        Prepare the module to run: store the context, validate/parse this
        module's own config section, subscribe to events it cares about.

        Must not have side effects on the outside world yet (no opening
        network connections, no starting background tasks) — that belongs
        in `start()`. Separating the two lets the kernel validate that
        *every* module can be constructed and configured correctly before
        *any* module goes live.
        """

    @abstractmethod
    async def start(self) -> None:
        """
        Begin the module's active work: start background tasks, open
        connections, begin publishing/consuming events in earnest.
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully stop the module's active work: cancel background
        tasks, close connections, unsubscribe from events. Must be safe
        to call even if `start()` partially failed.
        """
