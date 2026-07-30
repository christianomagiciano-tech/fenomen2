# Phase 0 Summary — Foundations

> **Status: COMPLETE** — verified on a real machine.

## What Was Implemented

- **Contracts** (`backend/contracts/`): the shared vocabulary every
  module and the kernel depend on — the `Module` base class and
  lifecycle states, the `Event` base class, kernel lifecycle events
  (`KernelStartingEvent`, `KernelStartedEvent`, `KernelStoppingEvent`,
  `KernelStoppedEvent`, `ModuleStateChangedEvent`), the error
  hierarchy, and the `KernelHealth`/`ModuleHealth` DTOs.
- **Event Bus** (`backend/kernel/event_bus/`): in-process, `asyncio`-
  native, typed publish/subscribe. Isolates failing handlers so one
  broken subscriber cannot break delivery to others or propagate back
  to the publisher.
- **Module Registry** (`backend/kernel/registry/`): tracks every
  registered module and enforces a strict lifecycle state-transition
  table (`UNLOADED → INITIALIZED → STARTED → STOPPED`, `FAILED`
  reachable from any state).
- **Config Manager** (`backend/kernel/config/`): loads a root YAML
  file; validates each section against a Pydantic schema on demand.
  Missing sections fall back to schema defaults; invalid ones raise
  `ConfigurationError` immediately.
- **Logging** (`backend/kernel/logging/`): one place that configures
  the entire `fenomen.*` logger hierarchy (console or JSON format).
  Modules never configure logging themselves.
- **Kernel / Lifecycle Orchestration** (`backend/kernel/lifecycle/`):
  ties the above together. Ordered, fail-fast startup. Graceful,
  fault-tolerant shutdown (a failing module's `stop()` is logged and
  isolated; shutdown continues with the rest), triggered by an OS
  termination signal or a direct call. Synchronous `health()` snapshot
  method.
- **Cross-Platform Shutdown Signals** (`backend/kernel/lifecycle/signals.py`):
  added after Windows verification surfaced that `loop.add_signal_handler()`
  is POSIX-only. Isolates the platform difference in one function —
  `Kernel` itself has no platform-specific code. See
  [ADR 0002](../architecture/decisions/0002-cross-platform-shutdown-signals.md).
- **Composition Root** (`backend/app.py`): the only file permitted to
  wire concrete modules into the kernel. Registers zero modules in
  Phase 0, per the roadmap.
- **Test Suite** (`backend/tests/`): unit tests for the event bus,
  registry, config manager, and cross-platform signal handling
  individually, plus a full integration suite
  (`test_kernel_integration.py`) exercising the entire
  start → run → stop lifecycle against a test-double module, including
  failure-handling paths (failing `initialize()`, failing `stop()`),
  DI verification, event-ordering verification, and graceful-shutdown-
  via-signal simulation.
- **Dev Tooling**: `pyproject.toml` (packaging + pytest + ruff config);
  `scripts/bootstrap.{sh,ps1}`, `scripts/test.{sh,ps1}`,
  `scripts/lint.{sh,ps1}` — Linux/macOS and Windows versions of each.
- **Documentation**: architecture overview, ADR 0001 (microkernel +
  event bus rationale), ADR 0002 (cross-platform shutdown signals),
  module documentation convention (for Phase 1 onward), setup guide
  (both platforms), root README.

## Why the Architecture Was Chosen

Full reasoning: [ADR 0001](../architecture/decisions/0001-microkernel-event-bus.md)
(microkernel + event bus) and
[ADR 0002](../architecture/decisions/0002-cross-platform-shutdown-signals.md)
(cross-platform shutdown). Short version: modules must be addable
independently over the project's long lifetime without touching
existing code, and platform differences must be isolated to a single
point rather than leaking into the orchestrator.

## Verification Results (final — confirmed on both platforms)

| Check | Linux | Windows 11 |
|---|---|---|
| `scripts/bootstrap.{sh,ps1}` — venv creation | ✅ Pass | ✅ Pass |
| Dependency install | ✅ Pass | ✅ Pass |
| Editable install | ✅ Pass | ✅ Pass |
| `pytest` — full suite | ✅ Pass | ✅ **46 passed, 0 failed** |
| `python -m backend.app`, then Ctrl+C — graceful shutdown | ✅ Pass (by design; POSIX signal path unchanged) | ✅ **Confirmed live**: clean `Kernel starting` → `Kernel running` → (Ctrl+C) → `Kernel stopping` → `Kernel stopped`, no errors |

Windows initially failed with `NotImplementedError` from
`loop.add_signal_handler()` (not implemented on Windows event loops).
Fixed by isolating platform-specific shutdown-signal logic into
`backend/kernel/lifecycle/signals.py` (see
[ADR 0002](../architecture/decisions/0002-cross-platform-shutdown-signals.md)),
then re-verified clean on Windows 11.

**Phase 0 is complete, fully cross-platform, and verified end-to-end on
both Linux and Windows 11.**

## What Remains for Phase 1

- Implement the `commands` module (first real module) and the `cli`
  interface, proving the module contract and event bus end-to-end with
  a real, useful feature rather than a test double.
- Add a module `README.md` per `docs/modules/README.md`'s template.
