# Fenomen 2 — Architecture Overview

This document describes the architecture as actually implemented, starting
from Phase 0. For the reasoning behind the core pattern, see
[`decisions/0001-microkernel-event-bus.md`](decisions/0001-microkernel-event-bus.md).

## The Kernel

The kernel (`backend/kernel/`) is the only code every module depends on.
It provides four services:

| Component | Location | Responsibility |
|---|---|---|
| Event Bus | `kernel/event_bus/bus.py` | Typed publish/subscribe messaging between modules. Phase 0: in-process, `asyncio`-native. |
| Module Registry | `kernel/registry/registry.py` | Tracks every registered module and enforces valid lifecycle-state transitions. |
| Config Manager | `kernel/config/manager.py` | Loads the root YAML config; validates each module's own config section against that module's declared schema. |
| Logging setup | `kernel/logging/setup.py` | Configures the `fenomen` logger hierarchy once, centrally. Modules receive a pre-built, module-tagged logger — they never configure logging themselves. |

`Kernel` (`kernel/lifecycle/kernel.py`) composes these four and adds
orchestration: ordered startup, graceful shutdown, and health reporting.

## The Module Contract

Every capability (present or future) implements `backend/contracts/module_base.py::Module`:

```
class Module(ABC):
    metadata: ModuleMetadata          # name, version, description
    async def initialize(context) -> None   # wire up, don't go live yet
    async def start(self) -> None           # begin active work
    async def stop(self) -> None            # gracefully release resources
```

A module receives everything it needs — the event bus, config manager,
and its own logger — through the `ModuleContext` passed to `initialize()`.
This is dependency injection by construction: there is no global/singleton
kernel instance anywhere in the codebase for a module to reach for
instead.

### Lifecycle States

```
UNLOADED -> INITIALIZED -> STARTED -> STOPPED
   \___________________________________/
                    |
                    v
                 FAILED   (reachable from any state)
```

The `ModuleRegistry` enforces this table; illegal transitions raise
`InvalidModuleStateTransitionError` rather than silently succeeding.

## Startup and Shutdown Sequence

**Startup** (`Kernel.start()`):
1. Publish `KernelStartingEvent`.
2. `initialize()` every registered module, in registration order.
3. `start()` every registered module, in registration order.
4. Publish `KernelStartedEvent`.

Startup is fail-fast: if any module's `initialize()` or `start()` raises,
the kernel stops immediately, transitions to `FAILED`, and the exception
propagates to the caller. Fenomen 2 does not run in a partially-started
state.

**Shutdown** (`Kernel.stop()`), triggered by `SIGINT`/`SIGTERM` or a direct
call:
1. Publish `KernelStoppingEvent`.
2. `stop()` every started module, in **reverse** registration order.
3. Publish `KernelStoppedEvent`.

Shutdown is fault-tolerant in the opposite direction from startup: if a
module's `stop()` raises, the error is logged, that module is marked
`FAILED`, and shutdown *continues* with the remaining modules. One
misbehaving module must never be able to hang or abort the whole
platform's shutdown.

## Health Reporting

`Kernel.health()` returns a `KernelHealth` snapshot (kernel state + every
module's name/version/state). It is a plain synchronous method in Phase 0
— no HTTP involved. `interfaces/api` (Phase 4) will expose the exact same
model over `GET /health`; the dashboard (also Phase 4+) consumes it from
there. Building the DTO now, decoupled from any transport, means Phase 4
adds a thin HTTP wrapper rather than designing the health data shape from
scratch.

## Repository Layout

```
fenomen2/
├── backend/
│   ├── contracts/       # Shared vocabulary: events, Module base, errors, health/kernel-state DTOs
│   ├── kernel/           # Event bus, registry, config, logging, lifecycle orchestration
│   ├── modules/           # First-party capability modules (empty in Phase 0)
│   ├── plugins/           # Dynamically-discovered third-party modules (Phase 6+)
│   ├── interfaces/         # api/ (Phase 4), cli/ (Phase 1) — ways the outside world reaches the kernel
│   ├── app.py               # Composition root — the only file that wires concrete modules into the kernel
│   └── tests/                # Test suite, mirroring backend/ structure
├── frontend/                  # Angular web dashboard (Phase 4+)
├── config/default.yaml         # Root configuration file
├── docs/                        # This directory
└── scripts/                      # Dev tooling
```

## What Phase 0 Deliberately Does Not Include

- **No product modules.** `backend/modules/` is empty. Phase 0 proves the
  kernel works using a test-only module (`backend/tests/kernel/support.py`)
  — not a real, shipped-but-incomplete module.
- **No dynamic plugin discovery.** Modules are registered explicitly in
  `app.py`. Manifest-based discovery is scoped to Phase 6, once there is
  an actual second module to justify the mechanism.
- **No networked event bus.** The in-process `asyncio` implementation is
  complete and permanent for single-node operation — it is not a
  placeholder. A networked implementation is a Phase 8 addition, not a
  Phase 0 shortcut waiting to be finished.
