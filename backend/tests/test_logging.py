"""Structured logging stays local."""

from __future__ import annotations

import json
from pathlib import Path

from app.logging import configure_logging, get_logger


def test_log_file_receives_json_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "backend.jsonl"
    configure_logging("INFO", log_file)
    get_logger("test").info("hello", step="P0-S05")
    for handler in __import__("logging").getLogger().handlers:
        handler.flush()
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line]
    assert lines[-1]["event"] == "hello"
    assert lines[-1]["step"] == "P0-S05"
    assert lines[-1]["level"] == "info"


def test_console_only_mode(tmp_path: Path) -> None:
    configure_logging("WARNING", None)
    get_logger("test").warning("no_file")
    assert list(tmp_path.iterdir()) == []


def test_logger_is_bound_logger() -> None:
    configure_logging("INFO", None)
    log = get_logger("x").bind(step="P0-S05")
    assert type(log).__name__.startswith("BoundLogger")
    assert callable(log.info)
    assert callable(log.bind(extra=1).warning)
