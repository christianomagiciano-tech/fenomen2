"""
Test-double module implementations.

These exist ONLY to exercise the `Module` contract and the kernel's
orchestration of it in tests. They are not shipped, registered, or
referenced anywhere outside `backend/tests/` — Phase 0 ships zero product
modules, per the roadmap.
"""

from __future__ import annotations

from backend.contracts.module_base import Module, ModuleContext, ModuleMetadata


class RecordingModule(Module):
    """
    A minimal, well-behaved module that records every lifecycle call it
    receives, so tests can assert on call order and on the context it was
    given.
    """

    def __init__(self, name: str = "recording-module", version: str = "0.1.0") -> None:
        self._metadata = ModuleMetadata(name=name, version=version, description="Test double.")
        self.calls: list[str] = []
        self.received_context: ModuleContext | None = None

    @property
    def metadata(self) -> ModuleMetadata:
        return self._metadata

    async def initialize(self, context: ModuleContext) -> None:
        self.calls.append("initialize")
        self.received_context = context

    async def start(self) -> None:
        self.calls.append("start")

    async def stop(self) -> None:
        self.calls.append("stop")


class FailingInitializeModule(Module):
    """A module whose `initialize()` always raises, to test startup failure handling."""

    def __init__(self, name: str = "failing-initialize-module") -> None:
        self._metadata = ModuleMetadata(name=name, version="0.1.0")

    @property
    def metadata(self) -> ModuleMetadata:
        return self._metadata

    async def initialize(self, context: ModuleContext) -> None:
        raise RuntimeError("simulated initialize failure")

    async def start(self) -> None:  # pragma: no cover - should never be reached
        raise AssertionError("start() must not be called if initialize() failed")

    async def stop(self) -> None:  # pragma: no cover - should never be reached
        raise AssertionError("stop() must not be called if initialize() failed")


class FailingStopModule(Module):
    """A module whose `stop()` always raises, to test that shutdown continues past it."""

    def __init__(self, name: str = "failing-stop-module") -> None:
        self._metadata = ModuleMetadata(name=name, version="0.1.0")

    @property
    def metadata(self) -> ModuleMetadata:
        return self._metadata

    async def initialize(self, context: ModuleContext) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        raise RuntimeError("simulated stop failure")
