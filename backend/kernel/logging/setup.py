"""
Centralized logging configuration.

`configure_logging()` is called exactly once, at kernel startup, by the
composition root (`app.py`). No module should call `logging.basicConfig()`
or add its own handlers — modules simply call
`logging.getLogger(f"fenomen.modules.{name}")` (handed to them pre-built
inside their `ModuleContext`, see `contracts.module_base.ModuleContext`)
and log through it. All formatting/output configuration lives here, in one
place, so changing log format or destination never requires touching
module code.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Literal

_ROOT_LOGGER_NAME = "fenomen"


class _JsonFormatter(logging.Formatter):
    """Formats each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(
    level: str = "INFO",
    fmt: Literal["console", "json"] = "console",
) -> None:
    """
    Configure the `fenomen` logger hierarchy. Safe to call more than once
    (e.g. in tests) — it replaces any handlers it previously installed
    rather than stacking duplicates.
    """
    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.setLevel(level)
    root_logger.propagate = False

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler: logging.Handler = logging.StreamHandler(stream=sys.stdout)
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_logger.addHandler(handler)
