"""
Cross-platform shutdown signal handling.

`asyncio`'s `loop.add_signal_handler()` only works on POSIX event loops —
on Windows it raises `NotImplementedError`
(https://docs.python.org/3/library/asyncio-platforms.html#windows). This
module is the single place that knows that, so `Kernel` and everything
else in the codebase can call one function and not care which platform
it's running on.
"""

from __future__ import annotations

import signal
import sys
from typing import TYPE_CHECKING, Any, Callable, Sequence

if TYPE_CHECKING:
    import asyncio

ShutdownCallback = Callable[[], None]


def _default_shutdown_signals() -> tuple[signal.Signals, ...]:
    """
    The signals that should trigger graceful shutdown, for the current
    platform.

    - POSIX: SIGINT (Ctrl+C) and SIGTERM (the standard "please stop"
      signal sent by process managers, `kill`, etc.).
    - Windows: SIGINT (Ctrl+C) and SIGBREAK (Ctrl+Break — the practical
      Windows equivalent of a second termination trigger). SIGTERM is
      also included since `signal.signal()` accepts it on Windows, but
      note it is rarely delivered there in practice — Windows has no
      POSIX-style external SIGTERM; termination is normally done via
      `TerminateProcess`, which cannot be intercepted at all.
    """
    if sys.platform == "win32":
        return (signal.SIGINT, signal.SIGBREAK, signal.SIGTERM)  # type: ignore[attr-defined]
    return (signal.SIGINT, signal.SIGTERM)


def install_shutdown_handlers(
    loop: "asyncio.AbstractEventLoop",
    on_signal: ShutdownCallback,
    *,
    signals: Sequence[signal.Signals] | None = None,
) -> Callable[[], None]:
    """
    Install OS signal handlers that call `on_signal` (a synchronous,
    zero-argument callable) when the process receives a termination
    signal.

    Returns an `uninstall()` callable that removes exactly the handlers
    this call installed, restoring whatever was registered before (on
    Windows) or removing the loop's handler (on POSIX). Safe to call
    `uninstall()` more than once.

    On POSIX, this delegates to `loop.add_signal_handler()`, which
    integrates signal delivery with the event loop directly. On Windows,
    where that raises `NotImplementedError`, this falls back to
    `signal.signal()`.
    """
    resolved_signals = tuple(signals) if signals is not None else _default_shutdown_signals()
    installed: list[signal.Signals] = []

    if sys.platform == "win32":
        previous_handlers: dict[signal.Signals, Any] = {}

        def _handler(signum: int, frame: Any) -> None:  # noqa: ANN401
            on_signal()

        for sig in resolved_signals:
            previous_handlers[sig] = signal.signal(sig, _handler)
            installed.append(sig)

        def uninstall() -> None:
            for sig in installed:
                signal.signal(sig, previous_handlers[sig])
            installed.clear()

        return uninstall

    for sig in resolved_signals:
        loop.add_signal_handler(sig, on_signal)
        installed.append(sig)

    def uninstall() -> None:
        for sig in installed:
            loop.remove_signal_handler(sig)
        installed.clear()

    return uninstall
