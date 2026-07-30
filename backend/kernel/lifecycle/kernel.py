"""
The `Kernel` — composition root behaviour for the platform.

`Kernel` owns one `EventBus` and one `ModuleRegistry` instance, and is
responsible for the ordered startup and shutdown of every registered
module. It is constructed once per running process by `app.py` (or by a
test). It is intentionally NOT a global/singleton — nothing in this
codebase reaches a `Kernel` except by being handed one explicitly, which
is what makes multiple kernels constructable side-by-side in tests.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from backend.contracts.errors import (
    InvalidKernelStateTransitionError,
    ModuleInitializationError,
    ModuleStartError,
)
from backend.contracts.events.kernel import (
    KernelStartedEvent,
    KernelStartingEvent,
    KernelStoppedEvent,
    KernelStoppingEvent,
    ModuleStateChangedEvent,
)
from backend.contracts.health import KernelHealth, ModuleHealth
from backend.contracts.kernel_state import KernelState
from backend.contracts.module_base import Module, ModuleContext, ModuleState
from backend.kernel.config.manager import ConfigManager
from backend.kernel.event_bus.bus import EventBus
from backend.kernel.lifecycle.signals import install_shutdown_handlers
from backend.kernel.registry.registry import ModuleRecord, ModuleRegistry

_MODULE_LOGGER_PREFIX = "fenomen.modules"


class Kernel:
    """Owns the event bus and module registry; orchestrates startup and shutdown."""

    def __init__(self, config: ConfigManager, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("fenomen.kernel")
        self._event_bus = EventBus()
        self._registry = ModuleRegistry()
        self._state = KernelState.NOT_STARTED
        self._shutdown_complete = asyncio.Event()
        self._stop_lock = asyncio.Lock()

    # -- Public accessors -------------------------------------------------

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def registry(self) -> ModuleRegistry:
        return self._registry

    @property
    def state(self) -> KernelState:
        return self._state

    def register_module(self, module: Module) -> ModuleRecord:
        """Register a module with the kernel. Must be called before `start()`."""
        return self._registry.register(module)

    # -- Startup ------------------------------------------------------------

    async def start(self) -> None:
        """
        Initialize, then start, every registered module, in registration
        order. If any module fails to initialize or start, startup stops
        immediately (fail-fast) — Fenomen 2 does not run in a partially-
        started state. The kernel transitions to FAILED and the exception
        propagates to the caller.
        """
        if self._state != KernelState.NOT_STARTED:
            raise InvalidKernelStateTransitionError(
                f"Cannot start kernel from state {self._state.value!r}; "
                "a kernel instance can only be started once."
            )

        self._state = KernelState.STARTING
        self._logger.info("Kernel starting (%d module(s) registered)", len(self._registry.all_records()))
        await self._event_bus.publish(KernelStartingEvent(source="kernel"))

        try:
            for record in self._registry.all_records():
                await self._initialize_module(record)
            for record in self._registry.all_records():
                await self._start_module(record)
        except (ModuleInitializationError, ModuleStartError):
            self._state = KernelState.FAILED
            self._logger.error("Kernel startup failed; see preceding log entries for details.")
            raise

        self._state = KernelState.RUNNING
        self._logger.info("Kernel running.")
        await self._event_bus.publish(
            KernelStartedEvent(source="kernel", module_count=len(self._registry.all_records()))
        )

    async def _initialize_module(self, record: ModuleRecord) -> None:
        name = record.name
        module_logger = logging.getLogger(f"{_MODULE_LOGGER_PREFIX}.{name}")
        context = ModuleContext(event_bus=self._event_bus, config=self._config, logger=module_logger)
        try:
            await record.module.initialize(context)
        except Exception as exc:
            await self._mark_failed(record)
            raise ModuleInitializationError(f"Module {name!r} failed to initialize") from exc
        await self._transition(record, ModuleState.INITIALIZED)

    async def _start_module(self, record: ModuleRecord) -> None:
        name = record.name
        try:
            await record.module.start()
        except Exception as exc:
            await self._mark_failed(record)
            raise ModuleStartError(f"Module {name!r} failed to start") from exc
        await self._transition(record, ModuleState.STARTED)

    # -- Shutdown -------------------------------------------------------------

    async def stop(self) -> None:
        """
        Gracefully stop every STARTED module, in *reverse* registration
        order (symmetric with startup — the last module to come up is the
        first to go down, mirroring typical resource-dependency order).

        A module that raises during `stop()` is logged and marked FAILED,
        but does NOT prevent the remaining modules from being stopped —
        graceful shutdown must not itself be able to hang or abort partway
        through because of one misbehaving module.

        Safe to call multiple times (or concurrently, e.g. once from a
        signal handler and once from a caller) — only the first call does
        the work.
        """
        async with self._stop_lock:
            if self._state in (KernelState.STOPPED, KernelState.STOPPING):
                return
            if self._state not in (KernelState.RUNNING, KernelState.FAILED, KernelState.STARTING):
                raise InvalidKernelStateTransitionError(
                    f"Cannot stop kernel from state {self._state.value!r}."
                )

            self._state = KernelState.STOPPING
            self._logger.info("Kernel stopping.")
            await self._event_bus.publish(KernelStoppingEvent(source="kernel"))

            for record in reversed(self._registry.all_records()):
                await self._stop_module(record)

            self._state = KernelState.STOPPED
            self._logger.info("Kernel stopped.")
            await self._event_bus.publish(KernelStoppedEvent(source="kernel"))
            self._shutdown_complete.set()

    async def _stop_module(self, record: ModuleRecord) -> None:
        if record.state != ModuleState.STARTED:
            # Nothing to stop for a module that never fully started.
            return
        try:
            await record.module.stop()
        except Exception:
            self._logger.exception("Module %r raised while stopping; continuing shutdown.", record.name)
            await self._mark_failed(record)
            return
        await self._transition(record, ModuleState.STOPPED)

    # -- Health ---------------------------------------------------------------

    def health(self) -> KernelHealth:
        """
        Return a point-in-time snapshot of kernel and module health. Cheap
        and synchronous by design — this is what Phase 4's HTTP `/health`
        endpoint will call directly.
        """
        return KernelHealth(
            state=self._state,
            modules=[
                ModuleHealth(name=r.name, version=r.module.metadata.version, state=r.state)
                for r in self._registry.all_records()
            ],
        )

    # -- Running as a long-lived process --------------------------------------

    async def run_until_shutdown(self, *, install_signal_handlers: bool = True) -> None:
        """
        Start the kernel and block until a graceful shutdown is triggered
        — either by an OS termination signal (when
        `install_signal_handlers=True`, the default for real process
        execution; handled cross-platform, see
        `backend.kernel.lifecycle.signals`) or by another task calling
        `stop()` directly (used in tests, where installing OS signal
        handlers is unnecessary and can conflict with the test runner's
        own handlers).
        """
        loop = asyncio.get_running_loop()
        uninstall: Callable[[], None] | None = None

        if install_signal_handlers:
            def _on_signal() -> None:
                asyncio.ensure_future(self.stop())

            uninstall = install_shutdown_handlers(loop, _on_signal)

        try:
            await self.start()
            await self._shutdown_complete.wait()
        finally:
            if uninstall is not None:
                uninstall()

    # -- Internal helpers -------------------------------------------------------

    async def _transition(self, record: ModuleRecord, new_state: ModuleState) -> None:
        previous_state = self._registry.transition(record.name, new_state)
        await self._publish_state_change(record.name, previous_state, new_state)

    async def _mark_failed(self, record: ModuleRecord) -> None:
        if record.state != ModuleState.FAILED:
            previous_state = self._registry.transition(record.name, ModuleState.FAILED)
            await self._publish_state_change(record.name, previous_state, ModuleState.FAILED)

    async def _publish_state_change(
        self, module_name: str, previous_state: ModuleState, new_state: ModuleState
    ) -> None:
        await self._event_bus.publish(
            ModuleStateChangedEvent(
                source="kernel",
                module_name=module_name,
                previous_state=previous_state,
                new_state=new_state,
            )
        )
