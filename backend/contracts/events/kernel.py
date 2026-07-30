"""
Events published by the kernel itself, describing its own lifecycle and the
lifecycle of the modules it manages.

Modules can subscribe to these to react to system-wide state changes (e.g.
a dashboard module might subscribe to `ModuleStateChangedEvent` to show a
live status board) without the kernel needing to know that dashboard
exists.
"""

from __future__ import annotations

from backend.contracts.events.base import Event
from backend.contracts.module_base import ModuleState


class KernelStartingEvent(Event):
    """Published once, before any module is initialized."""


class KernelStartedEvent(Event):
    """Published once all registered modules have successfully started."""

    module_count: int


class KernelStoppingEvent(Event):
    """Published once, before any module is stopped, when shutdown begins."""


class KernelStoppedEvent(Event):
    """Published once all modules have been stopped (or shutdown gave up)."""


class ModuleStateChangedEvent(Event):
    """Published whenever a module transitions from one lifecycle state to another."""

    module_name: str
    previous_state: ModuleState
    new_state: ModuleState
