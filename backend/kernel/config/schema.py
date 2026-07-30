"""The kernel's own configuration section (the `kernel:` key in config YAML)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KernelConfig(BaseModel):
    """
    Configuration for the kernel itself, independent of any module.

    Read from the `kernel:` section of the root config file.
    """

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"
    shutdown_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description=(
            "Maximum time to wait for all modules to stop during graceful "
            "shutdown before giving up and forcing exit."
        ),
    )
