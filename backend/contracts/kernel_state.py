"""The kernel's own lifecycle state — distinct from any individual module's state."""

from __future__ import annotations

from enum import Enum


class KernelState(str, Enum):
    """
    Lifecycle states of the kernel itself.

    Valid transitions: NOT_STARTED -> STARTING -> RUNNING -> STOPPING -> STOPPED.
    FAILED is reachable from STARTING or RUNNING if startup or a module
    operation fails unrecoverably.
    """

    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
