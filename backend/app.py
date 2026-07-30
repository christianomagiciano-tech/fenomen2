"""
Composition root.

This is the only file in the codebase allowed to import concrete modules
and wire them into the kernel — everything else depends only on
`backend.contracts`. For Phase 0, zero product modules exist yet (per the
roadmap), so this boots a kernel with an empty module list and simply
demonstrates a clean, signal-driven start/stop cycle.

Run with:
    python -m backend.app
Stop with Ctrl+C (SIGINT) or SIGTERM — both trigger graceful shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.kernel.config.manager import ConfigManager
from backend.kernel.config.schema import KernelConfig
from backend.kernel.lifecycle.kernel import Kernel
from backend.kernel.logging.setup import configure_logging

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


def build_kernel(config_path: Path = _DEFAULT_CONFIG_PATH) -> Kernel:
    """
    Construct a fully-wired, not-yet-started `Kernel`.

    Split out from `main()` so tests can build a kernel the exact same way
    the real process does, without going through `asyncio.run`.
    """
    config = ConfigManager.from_yaml_file(config_path)
    kernel_config = config.get_section("kernel", KernelConfig)
    configure_logging(level=kernel_config.log_level, fmt=kernel_config.log_format)

    kernel = Kernel(config=config, logger=logging.getLogger("fenomen.kernel"))

    # Phase 0 registers no product modules — this loop is intentionally
    # empty. Phase 1 onward will add lines like:
    #     kernel.register_module(CommandModule())
    # here, and nowhere else.

    return kernel


async def main() -> None:
    kernel = build_kernel()
    await kernel.run_until_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
