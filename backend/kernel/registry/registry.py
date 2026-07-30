"""
The module registry.

Tracks every module known to the kernel, its current lifecycle state, and
enforces that only valid state transitions occur. The registry does not
itself call `initialize()`/`start()`/`stop()` on modules — that
orchestration lives in `backend.kernel.lifecycle.Kernel`. The registry's
only job is bookkeeping: "what modules exist, and what state is each one
in" — kept separate so it can be queried (e.g. by a future dashboard
module) without needing to also own orchestration logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.contracts.errors import (
    InvalidModuleStateTransitionError,
    ModuleAlreadyRegisteredError,
    ModuleNotFoundError,
)
from backend.contracts.module_base import Module, ModuleState

_logger = logging.getLogger("fenomen.kernel.registry")

# Explicit table of allowed transitions. FAILED is reachable from any
# state (a module can fail during initialize, start, or stop), which is
# why it is added programmatically below rather than listed per-state.
_ALLOWED_TRANSITIONS: dict[ModuleState, set[ModuleState]] = {
    ModuleState.UNLOADED: {ModuleState.INITIALIZED},
    ModuleState.INITIALIZED: {ModuleState.STARTED},
    ModuleState.STARTED: {ModuleState.STOPPED},
    ModuleState.STOPPED: {ModuleState.INITIALIZED},  # allows future re-init/reload
    ModuleState.FAILED: set(),  # a failed module must be re-registered, not resumed
}
for _state in list(_ALLOWED_TRANSITIONS):
    _ALLOWED_TRANSITIONS[_state] = _ALLOWED_TRANSITIONS[_state] | {ModuleState.FAILED}


@dataclass
class ModuleRecord:
    """A registered module together with its bookkeeping state."""

    module: Module
    state: ModuleState = ModuleState.UNLOADED
    _history: list[ModuleState] = field(default_factory=lambda: [ModuleState.UNLOADED])

    @property
    def name(self) -> str:
        return self.module.metadata.name

    @property
    def history(self) -> tuple[ModuleState, ...]:
        return tuple(self._history)


class ModuleRegistry:
    """Holds every module the kernel knows about, keyed by module name."""

    def __init__(self) -> None:
        self._records: dict[str, ModuleRecord] = {}

    def register(self, module: Module) -> ModuleRecord:
        """
        Register a new module instance. Raises
        :class:`ModuleAlreadyRegisteredError` if a module with the same
        `metadata.name` is already registered.
        """
        name = module.metadata.name
        if name in self._records:
            raise ModuleAlreadyRegisteredError(
                f"A module named {name!r} is already registered."
            )
        record = ModuleRecord(module=module)
        self._records[name] = record
        _logger.info("Module %r registered (version=%s)", name, module.metadata.version)
        return record

    def get(self, name: str) -> ModuleRecord:
        """Look up a registered module's record by name. Raises :class:`ModuleNotFoundError` if unknown."""
        try:
            return self._records[name]
        except KeyError as exc:
            raise ModuleNotFoundError(f"No module named {name!r} is registered.") from exc

    def all_records(self) -> tuple[ModuleRecord, ...]:
        """All registered module records, in registration order."""
        return tuple(self._records.values())

    def transition(self, name: str, new_state: ModuleState) -> ModuleState:
        """
        Move a module to `new_state`, enforcing the allowed-transition
        table. Returns the previous state (useful for emitting a
        `ModuleStateChangedEvent`). Raises
        :class:`InvalidModuleStateTransitionError` on an illegal move.
        """
        record = self.get(name)
        previous_state = record.state
        if new_state not in _ALLOWED_TRANSITIONS[previous_state]:
            raise InvalidModuleStateTransitionError(
                f"Module {name!r} cannot transition from {previous_state.value!r} "
                f"to {new_state.value!r}."
            )
        record.state = new_state
        record._history.append(new_state)
        _logger.info(
            "Module %r transitioned %s -> %s", name, previous_state.value, new_state.value
        )
        return previous_state
