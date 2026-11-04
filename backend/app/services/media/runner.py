"""Subprocess execution for FFmpeg jobs (no shell, structured logging, progress)."""

from __future__ import annotations

import subprocess
import tempfile
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.logging import get_logger
from app.services.media.progress import ProgressEvent, parse_progress_block

LOG = get_logger(__name__)
MAX_STDOUT_CHARS = 8 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024


class CommandCancelledError(RuntimeError):
    """Raised after a requested cancellation has killed and reaped the child."""


class CommandFailedError(RuntimeError):
    """Raised when FFmpeg exits non-zero. The stderr tail is preserved."""

    def __init__(self, args: Sequence[str], returncode: int, stderr_tail: str) -> None:
        self.args_list = list(args)
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        super().__init__(f"command failed with exit code {returncode}: {stderr_tail[-400:]}")


@dataclass
class CommandResult:
    """Outcome of a successful command."""

    returncode: int
    stdout: str
    stderr: str


def run_command(
    args: Sequence[str],
    *,
    timeout: float | None = None,
    on_progress: Callable[[ProgressEvent], None] | None = None,
    total_seconds: float | None = None,
    cwd: Path | None = None,
    cancel_event: threading.Event | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a command without a shell, streaming ``-progress`` blocks to ``on_progress``."""
    LOG.info("media.command.start", argv=[str(part) for part in args])
    if cancel_event is not None and cancel_event.is_set():
        LOG.info("media.command.cancelled_before_start")
        raise CommandCancelledError("Media task cancelled")
    # A file, rather than an undrained pipe, prevents stderr back-pressure deadlocks.
    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        process = subprocess.Popen(
            [str(part) for part in args],
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd) if cwd else None,
            env=env,
        )
        timed_out = threading.Event()
        stopped = threading.Event()

        def monitor() -> None:
            while not stopped.wait(0.05):
                if cancel_event is not None and cancel_event.is_set():
                    process.kill()
                    return

        def kill_on_timeout() -> None:
            timed_out.set()
            process.kill()

        timer = threading.Timer(timeout, kill_on_timeout) if timeout else None
        watcher = (
            threading.Thread(target=monitor, daemon=True) if cancel_event is not None else None
        )
        if timer is not None:
            timer.daemon = True
            timer.start()
        if watcher is not None:
            watcher.start()
        try:
            stdout = _collect_stdout(process, on_progress, total_seconds)
            returncode = process.wait()
        finally:
            _reap(process, stopped, timer, watcher)
        stderr_file.seek(0, 2)
        stderr_file.seek(max(0, stderr_file.tell() - MAX_STDERR_BYTES))
        stderr = stderr_file.read().decode("utf-8", errors="replace")
    if timed_out.is_set():
        LOG.error("media.command.timeout", argv=[str(part) for part in args], timeout=timeout)
        raise TimeoutError(f"command timed out after {timeout}s")
    if cancel_event is not None and cancel_event.is_set():
        LOG.info("media.command.cancelled", argv=[str(part) for part in args])
        raise CommandCancelledError("Media task cancelled")
    if returncode != 0:
        LOG.error("media.command.failed", returncode=returncode, stderr=stderr[-2000:])
        raise CommandFailedError(args, returncode, stderr)
    LOG.info("media.command.done", returncode=returncode)
    return CommandResult(returncode=returncode, stdout=stdout, stderr=stderr)


def _collect_stdout(
    process: subprocess.Popen[str],
    callback: Callable[[ProgressEvent], None] | None,
    total: float | None,
) -> str:
    block: list[str] = []
    lines: list[str] = []
    assert process.stdout is not None
    size = 0
    for line in iter(lambda: process.stdout.readline(MAX_STDOUT_CHARS + 1), ""):
        size += len(line)
        if size > MAX_STDOUT_CHARS:
            LOG.error("media.command.stdout_limit", limit=MAX_STDOUT_CHARS)
            raise RuntimeError("Command output exceeded the 8 MiB safety limit")
        lines.append(line)
        if callback is not None:
            block.append(line)
            if line.startswith("progress="):
                event = parse_progress_block("".join(block), total)
                block.clear()
                if event is not None:
                    callback(event)
    return "".join(lines)


def _reap(
    process: subprocess.Popen[str],
    stopped: threading.Event,
    timer: threading.Timer | None,
    watcher: threading.Thread | None,
) -> None:
    stopped.set()
    if timer is not None:
        timer.cancel()
        timer.join(timeout=1)
    if process.poll() is None:
        process.kill()
    process.wait()
    if watcher is not None:
        watcher.join(timeout=1)
    if process.stdout is not None:
        process.stdout.close()
