# ADR 0002: Cross-Platform Shutdown Signal Handling

- **Status**: Accepted
- **Date**: Phase 0 (post-Windows verification)

## Context

`Kernel.run_until_shutdown()` used `loop.add_signal_handler(sig, handler)`
to trigger graceful shutdown on SIGINT/SIGTERM. This works on POSIX event
loops but raises `NotImplementedError` on Windows — `asyncio`'s Windows
event loops (both `ProactorEventLoop` and `SelectorEventLoop`) do not
implement loop-integrated signal handling
(https://docs.python.org/3/library/asyncio-platforms.html#windows).
This was confirmed by running Phase 0 on a real Windows 11 machine.

Fenomen 2 must run on Windows as a development platform (per the
project's stated tooling — VS Code, Git — even though Linux/Ubuntu is
the primary target), so this needed a real fix, not a workaround at the
call site.

## Decision

Isolate all platform-specific signal-handling logic in one new module,
`backend/kernel/lifecycle/signals.py`, exposing a single function:
`install_shutdown_handlers(loop, on_signal, *, signals=None) -> uninstall`.

- On POSIX, it uses `loop.add_signal_handler()`, unchanged from before.
- On Windows, it uses `signal.signal()` directly. This is safe to combine
  with asyncio because CPython guarantees Python-level signal handlers
  registered via `signal.signal()` run on the main thread, at a bytecode
  boundary — the same thread the event loop runs on — so scheduling an
  asyncio task from inside the handler works correctly.
- Platform detection is a single `sys.platform == "win32"` check, made
  once, inside this module only. `Kernel` calls
  `install_shutdown_handlers()` and never itself branches on platform.

The default signal set also differs slightly: Windows additionally
listens for `SIGBREAK` (Ctrl+Break), the practical Windows equivalent of
a second termination trigger alongside Ctrl+C's `SIGINT`. `SIGTERM` is
still included on Windows for API symmetry, though it is rarely actually
delivered there in practice.

## Consequences

**Positive**

- `Kernel` remains fully platform-agnostic — no `if sys.platform`
  anywhere in the orchestrator itself, satisfying "no platform-specific
  hacks" as a codebase-wide property, not just a promise.
- The platform difference is unit-testable without needing to actually
  run on both operating systems: `test_signals.py` monkeypatches
  `sys.platform` and, for the Windows path, `signal.signal` itself, to
  verify each strategy is chosen and behaves correctly.
- Adding a third strategy later (unlikely, but e.g. a signal-handling
  approach for an embedded/constrained runtime) means adding a branch
  in one function, not auditing every caller of the old
  `loop.add_signal_handler()` call.

**Negative / accepted trade-offs**

- Windows graceful shutdown is not triggered by `taskkill` without
  `/f` in all cases, since Windows process termination tools mostly use
  `TerminateProcess`, which cannot be intercepted by any handler,
  POSIX-style or not. Ctrl+C and Ctrl+Break in an interactive console are
  reliably caught; that is the primary interactive-development scenario
  this addresses. Production process-manager-driven shutdown on Windows
  is out of scope until (if) Windows is ever targeted as a deployment
  platform — the project's actual deployment target is Linux.
