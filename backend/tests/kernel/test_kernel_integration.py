"""
End-to-end integration tests for the kernel.

These are the tests that validate the *whole point* of Phase 0: a module
implementing only the `Module` contract can be registered, started,
communicate purely via the event bus, report correct health, and be
stopped gracefully — without the kernel or any other module knowing
anything about its internals.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.contracts.errors import (
    InvalidKernelStateTransitionError,
    ModuleInitializationError,
)
from backend.contracts.events.kernel import (
    KernelStartedEvent,
    KernelStartingEvent,
    KernelStoppedEvent,
    KernelStoppingEvent,
    ModuleStateChangedEvent,
)
from backend.contracts.kernel_state import KernelState
from backend.contracts.module_base import ModuleState
from backend.kernel.config.manager import ConfigManager
from backend.kernel.lifecycle.kernel import Kernel
from backend.tests.kernel.support import (
    FailingInitializeModule,
    FailingStopModule,
    RecordingModule,
)


def _make_kernel() -> Kernel:
    return Kernel(config=ConfigManager(raw_config={}))


async def test_module_lifecycle_calls_happen_in_correct_order() -> None:
    kernel = _make_kernel()
    module = RecordingModule(name="alpha")
    kernel.register_module(module)

    await kernel.start()
    assert module.calls == ["initialize", "start"]
    assert kernel.registry.get("alpha").state == ModuleState.STARTED
    assert kernel.state == KernelState.RUNNING

    await kernel.stop()
    assert module.calls == ["initialize", "start", "stop"]
    assert kernel.registry.get("alpha").state == ModuleState.STOPPED
    assert kernel.state == KernelState.STOPPED


async def test_module_receives_working_context_via_dependency_injection() -> None:
    """
    Proves DI end-to-end: the module never imports or reaches for the
    kernel's event bus globally — it is handed one, and that one actually
    works (round-trips a publish/subscribe through it).
    """
    kernel = _make_kernel()
    module = RecordingModule(name="alpha")
    kernel.register_module(module)
    await kernel.start()

    assert module.received_context is not None
    assert module.received_context.event_bus is kernel.event_bus

    received = []

    async def handler(event: KernelStoppingEvent) -> None:
        received.append(event)

    module.received_context.event_bus.subscribe(KernelStoppingEvent, handler)
    await kernel.stop()

    assert len(received) == 1


async def test_modules_start_in_registration_order_and_stop_in_reverse() -> None:
    kernel = _make_kernel()
    order: list[str] = []

    class OrderTrackingModule(RecordingModule):
        async def start(self) -> None:
            await super().start()
            order.append(f"start:{self.metadata.name}")

        async def stop(self) -> None:
            await super().stop()
            order.append(f"stop:{self.metadata.name}")

    kernel.register_module(OrderTrackingModule(name="first"))
    kernel.register_module(OrderTrackingModule(name="second"))
    kernel.register_module(OrderTrackingModule(name="third"))

    await kernel.start()
    await kernel.stop()

    assert order == [
        "start:first",
        "start:second",
        "start:third",
        "stop:third",
        "stop:second",
        "stop:first",
    ]


async def test_kernel_publishes_its_own_lifecycle_events() -> None:
    kernel = _make_kernel()
    seen: list[type] = []

    async def track(event) -> None:  # noqa: ANN001
        seen.append(type(event))

    kernel.event_bus.subscribe(KernelStartingEvent, track)
    kernel.event_bus.subscribe(KernelStartedEvent, track)
    kernel.event_bus.subscribe(KernelStoppingEvent, track)
    kernel.event_bus.subscribe(KernelStoppedEvent, track)

    await kernel.start()
    await kernel.stop()

    assert seen == [
        KernelStartingEvent,
        KernelStartedEvent,
        KernelStoppingEvent,
        KernelStoppedEvent,
    ]


async def test_kernel_publishes_module_state_changed_events() -> None:
    kernel = _make_kernel()
    kernel.register_module(RecordingModule(name="alpha"))

    changes: list[tuple[str, str]] = []

    async def track(event: ModuleStateChangedEvent) -> None:
        changes.append((event.previous_state.value, event.new_state.value))

    kernel.event_bus.subscribe(ModuleStateChangedEvent, track)

    await kernel.start()
    await kernel.stop()

    assert changes == [
        ("unloaded", "initialized"),
        ("initialized", "started"),
        ("started", "stopped"),
    ]


async def test_failing_module_initialize_fails_startup_and_marks_kernel_failed() -> None:
    kernel = _make_kernel()
    kernel.register_module(FailingInitializeModule(name="broken"))

    with pytest.raises(ModuleInitializationError):
        await kernel.start()

    assert kernel.state == KernelState.FAILED
    assert kernel.registry.get("broken").state == ModuleState.FAILED


async def test_failing_module_stop_does_not_block_other_modules_from_stopping() -> None:
    kernel = _make_kernel()
    healthy_before = RecordingModule(name="before")
    broken = FailingStopModule(name="broken")
    healthy_after = RecordingModule(name="after")

    kernel.register_module(healthy_before)
    kernel.register_module(broken)
    kernel.register_module(healthy_after)

    await kernel.start()
    await kernel.stop()  # must not raise, despite `broken.stop()` raising

    assert kernel.registry.get("before").state == ModuleState.STOPPED
    assert kernel.registry.get("after").state == ModuleState.STOPPED
    assert kernel.registry.get("broken").state == ModuleState.FAILED
    assert kernel.state == KernelState.STOPPED


async def test_double_start_raises() -> None:
    kernel = _make_kernel()
    await kernel.start()

    with pytest.raises(InvalidKernelStateTransitionError):
        await kernel.start()

    await kernel.stop()


async def test_stop_before_start_raises() -> None:
    kernel = _make_kernel()

    with pytest.raises(InvalidKernelStateTransitionError):
        await kernel.stop()


async def test_stop_is_idempotent() -> None:
    kernel = _make_kernel()
    await kernel.start()

    await kernel.stop()
    await kernel.stop()  # must not raise or double-run module.stop()

    assert kernel.state == KernelState.STOPPED


async def test_health_reflects_kernel_and_module_state_through_lifecycle() -> None:
    kernel = _make_kernel()
    kernel.register_module(RecordingModule(name="alpha", version="1.2.3"))

    health = kernel.health()
    assert health.state == KernelState.NOT_STARTED
    assert health.modules == [] or health.modules[0].state == ModuleState.UNLOADED
    assert health.is_healthy is False

    await kernel.start()
    health = kernel.health()
    assert health.state == KernelState.RUNNING
    assert len(health.modules) == 1
    assert health.modules[0].name == "alpha"
    assert health.modules[0].version == "1.2.3"
    assert health.modules[0].state == ModuleState.STARTED
    assert health.is_healthy is True

    await kernel.stop()
    health = kernel.health()
    assert health.state == KernelState.STOPPED
    assert health.is_healthy is False  # STOPPED is not RUNNING, by design


async def test_health_reports_unhealthy_when_a_module_has_failed() -> None:
    kernel = _make_kernel()
    kernel.register_module(FailingInitializeModule(name="broken"))

    with pytest.raises(ModuleInitializationError):
        await kernel.start()

    health = kernel.health()
    assert health.state == KernelState.FAILED
    assert health.is_healthy is False


async def test_run_until_shutdown_returns_after_stop_is_called_elsewhere() -> None:
    """
    Simulates graceful shutdown without installing real OS signal handlers
    (tests run under a test-runner-owned event loop where that would be
    invasive) — this is what `install_signal_handlers=False` is for.
    """
    kernel = _make_kernel()
    module = RecordingModule(name="alpha")
    kernel.register_module(module)

    async def trigger_shutdown_shortly() -> None:
        await asyncio.sleep(0.05)
        await kernel.stop()

    await asyncio.gather(
        kernel.run_until_shutdown(install_signal_handlers=False),
        trigger_shutdown_shortly(),
    )

    assert module.calls == ["initialize", "start", "stop"]
    assert kernel.state == KernelState.STOPPED
