"""Structured logging (structlog) with an optional local JSONL log file.

No log shipper, no network sink: logs stay on disk so the app remains offline.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import structlog

_CONSOLE_HANDLER_NAME = "cutting-edge-console"
_FILE_HANDLER_NAME = "cutting-edge-file"


def _build_handlers(level: int, log_file: Path | None) -> list[logging.Handler]:
    handlers: list[logging.Handler] = []
    console = logging.StreamHandler()
    console.set_name(_CONSOLE_HANDLER_NAME)
    console.setLevel(level)
    handlers.append(console)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=8 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.set_name(_FILE_HANDLER_NAME)
        file_handler.setLevel(level)
        handlers.append(file_handler)
    return handlers


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure structlog + stdlib logging exactly once per level/file pair."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
        existing.close()  # avoid leaking file descriptors between reconfigure calls
    for handler in _build_handlers(numeric_level, log_file):
        root.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
