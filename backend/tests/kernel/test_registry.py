from __future__ import annotations

import pytest

from backend.contracts.errors import (
    InvalidModuleStateTransitionError,
    ModuleAlreadyRegisteredError,
    ModuleNotFoundError,
)
from backend.contracts.module_base import ModuleState
from backend.kernel.registry.registry import ModuleRegistry
from backend.tests.kernel.support import RecordingModule


def test_register_and_get_module() -> None:
    registry = ModuleRegistry()
    module = RecordingModule(name="alpha")

    record = registry.register(module)

    assert record.name == "alpha"
    assert record.state == ModuleState.UNLOADED
    assert registry.get("alpha") is record


def test_registering_duplicate_name_raises() -> None:
    registry = ModuleRegistry()
    registry.register(RecordingModule(name="alpha"))

    with pytest.raises(ModuleAlreadyRegisteredError):
        registry.register(RecordingModule(name="alpha"))


def test_getting_unknown_module_raises() -> None:
    registry = ModuleRegistry()
    with pytest.raises(ModuleNotFoundError):
        registry.get("does-not-exist")


def test_valid_transition_sequence() -> None:
    registry = ModuleRegistry()
    registry.register(RecordingModule(name="alpha"))

    registry.transition("alpha", ModuleState.INITIALIZED)
    registry.transition("alpha", ModuleState.STARTED)
    registry.transition("alpha", ModuleState.STOPPED)

    record = registry.get("alpha")
    assert record.state == ModuleState.STOPPED
    assert record.history == (
        ModuleState.UNLOADED,
        ModuleState.INITIALIZED,
        ModuleState.STARTED,
        ModuleState.STOPPED,
    )


def test_invalid_transition_raises_and_leaves_state_unchanged() -> None:
    registry = ModuleRegistry()
    registry.register(RecordingModule(name="alpha"))

    with pytest.raises(InvalidModuleStateTransitionError):
        registry.transition("alpha", ModuleState.STARTED)  # cannot skip INITIALIZED

    assert registry.get("alpha").state == ModuleState.UNLOADED


def test_transition_to_failed_allowed_from_any_state() -> None:
    registry = ModuleRegistry()
    registry.register(RecordingModule(name="alpha"))

    registry.transition("alpha", ModuleState.FAILED)

    assert registry.get("alpha").state == ModuleState.FAILED


def test_all_records_preserves_registration_order() -> None:
    registry = ModuleRegistry()
    registry.register(RecordingModule(name="first"))
    registry.register(RecordingModule(name="second"))
    registry.register(RecordingModule(name="third"))

    names = [record.name for record in registry.all_records()]
    assert names == ["first", "second", "third"]
