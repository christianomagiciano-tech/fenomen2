"""
Health/status DTOs.

These are deliberately plain, serializable Pydantic models with no
behaviour. Phase 0 exposes them via `Kernel.health()` as a plain Python
call. Phase 4's `interfaces/api` will serve the exact same models over
HTTP (e.g. `GET /health`) — the shape does not need to change, only the
transport wrapping it.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.contracts.kernel_state import KernelState
from backend.contracts.module_base import ModuleState


class ModuleHealth(BaseModel):
    """Health/status snapshot of a single registered module."""

    name: str
    version: str
    state: ModuleState


class KernelHealth(BaseModel):
    """Health/status snapshot of the kernel and every module it manages."""

    state: KernelState
    modules: list[ModuleHealth]

    @property
    def is_healthy(self) -> bool:
        """
        True if the kernel is RUNNING and no module has FAILED.

        A simple, conservative definition deliberately chosen for Phase 0:
        "healthy" means "doing what it was asked to do, fully." Finer-
        grained health semantics (e.g. "degraded but operational") can be
        introduced later without breaking this field, since it is derived
        rather than stored.
        """
        return self.state == KernelState.RUNNING and all(
            module.state != ModuleState.FAILED for module in self.modules
        )
