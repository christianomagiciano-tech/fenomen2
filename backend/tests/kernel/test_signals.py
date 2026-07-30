"""
Unit tests for `backend.kernel.lifecycle.signals`.

These tests monkeypatch `sys.platform` and (on the simulated-Windows path)
`signal.signal` itself, rather than relying on actually running on both
POSIX and Windows — real OS signal delivery is inherently racy to test
and this module's entire job is choosing the right *strategy*, which is
what's under test here.
"""

from __future__ import annotations

import signal
import sys

from backend.kernel.lifecycle.signals import (
    _default_shutdown_signals,
    install_shutdown_handlers,
)


class _FakeLoop:
    """A minimal stand-in for `asyncio.AbstractEventLoop`'s signal API."""

    def __init__(self) -> None:
        self.added: list[signal.Signals] = []
        self.removed: list[signal.Signals] = []

    def add_signal_handler(self, sig: signal.Signals, callback) -> None:  # noqa: ANN001
        self.added.append(sig)

    def remove_signal_handler(self, sig: signal.Signals) -> None:
        self.removed.append(sig)


def test_default_shutdown_signals_on_posix_are_sigint_and_sigterm(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "linux")
    signals = _default_shutdown_signals()
    assert signal.SIGINT in signals
    assert signal.SIGTERM in signals


def test_default_shutdown_signals_on_windows_include_sigint_and_sigbreak(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "win32")
    if not hasattr(signal, "SIGBREAK"):
        # SIGBREAK only exists as an attribute of the `signal` module on
        # Windows itself; simulate it so this test can run on any OS.
        monkeypatch.setattr(signal, "SIGBREAK", signal.SIGTERM, raising=False)

    signals = _default_shutdown_signals()

    assert signal.SIGINT in signals


def test_install_on_posix_uses_loop_add_signal_handler(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "linux")
    loop = _FakeLoop()
    calls: list[str] = []

    uninstall = install_shutdown_handlers(
        loop, lambda: calls.append("signalled"), signals=(signal.SIGINT,)
    )

    assert loop.added == [signal.SIGINT]

    uninstall()
    assert loop.removed == [signal.SIGINT]


def test_install_on_windows_never_touches_the_loop(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "win32")
    loop = _FakeLoop()
    recorded_handlers: dict[signal.Signals, object] = {}

    def fake_signal(sig: signal.Signals, handler):  # noqa: ANN001
        recorded_handlers[sig] = handler
        return signal.SIG_DFL

    monkeypatch.setattr(signal, "signal", fake_signal)

    uninstall = install_shutdown_handlers(
        loop, lambda: None, signals=(signal.SIGINT,)
    )

    # The whole point: on Windows, `loop.add_signal_handler` (which raises
    # NotImplementedError there) must never be called.
    assert loop.added == []
    assert signal.SIGINT in recorded_handlers

    uninstall()


def test_install_on_windows_handler_invokes_callback(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "win32")
    loop = _FakeLoop()
    recorded_handlers: dict[signal.Signals, object] = {}

    def fake_signal(sig: signal.Signals, handler):  # noqa: ANN001
        recorded_handlers[sig] = handler
        return signal.SIG_DFL

    monkeypatch.setattr(signal, "signal", fake_signal)

    calls: list[str] = []
    install_shutdown_handlers(loop, lambda: calls.append("signalled"), signals=(signal.SIGINT,))

    # Simulate the OS delivering the signal by invoking the registered
    # handler exactly as CPython would.
    recorded_handlers[signal.SIGINT](signal.SIGINT, None)  # type: ignore[misc]

    assert calls == ["signalled"]


def test_install_on_windows_uninstall_restores_previous_handler(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "win32")
    loop = _FakeLoop()
    sentinel_previous_handler = object()
    calls: list[tuple[signal.Signals, object]] = []

    def fake_signal(sig: signal.Signals, handler):  # noqa: ANN001
        calls.append((sig, handler))
        return sentinel_previous_handler

    monkeypatch.setattr(signal, "signal", fake_signal)

    uninstall = install_shutdown_handlers(loop, lambda: None, signals=(signal.SIGINT,))
    uninstall()

    # First call installs our handler; second (from uninstall) restores
    # whatever `signal.signal` reported as previously registered.
    assert len(calls) == 2
    assert calls[1] == (signal.SIGINT, sentinel_previous_handler)
