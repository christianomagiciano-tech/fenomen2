"""
Shared exception hierarchy for Fenomen 2.

Every error raised anywhere in the platform (kernel, modules, plugins,
interfaces) should ultimately derive from :class:`FenomenError`. This lets
top-level error handling (e.g. in the CLI or API interface) catch
"anything the platform itself raised" distinctly from unexpected,
unhandled exceptions bubbling up from third-party libraries.
"""

from __future__ import annotations


class FenomenError(Exception):
    """Base class for all errors raised by Fenomen 2 code."""


class ConfigurationError(FenomenError):
    """Raised when configuration is missing, malformed, or fails validation."""


class EventBusError(FenomenError):
    """Raised for errors originating in the event bus itself.

    Errors raised *by event handlers* are deliberately NOT wrapped in this
    type — they are logged and isolated by the bus so one failing handler
    cannot break delivery to others. See EventBus.publish().
    """


class ModuleError(FenomenError):
    """Base class for errors related to module lifecycle or registration."""


class ModuleAlreadyRegisteredError(ModuleError):
    """Raised when attempting to register a module name that already exists."""


class ModuleNotFoundError(ModuleError):
    """Raised when referencing a module name that is not registered."""


class InvalidModuleStateTransitionError(ModuleError):
    """Raised when a module lifecycle transition is not permitted.

    For example, attempting to `start()` a module that has not yet been
    `initialize()`-d, or `initialize()`-ing a module twice.
    """


class ModuleInitializationError(ModuleError):
    """Raised when a module's initialize() coroutine raises or fails."""


class ModuleStartError(ModuleError):
    """Raised when a module's start() coroutine raises or fails."""


class ModuleStopError(ModuleError):
    """Raised when a module's stop() coroutine raises or fails."""


class KernelError(FenomenError):
    """Base class for errors related to the kernel's own lifecycle."""


class InvalidKernelStateTransitionError(KernelError):
    """Raised when an operation is requested that the kernel's current state does not permit.

    For example, calling `start()` on a kernel that is already RUNNING, or
    `stop()` on one that has never been started.
    """
