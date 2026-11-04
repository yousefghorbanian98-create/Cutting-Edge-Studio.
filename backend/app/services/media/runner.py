"""Subprocess execution for FFmpeg jobs (no shell, structured logging, progress)."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.logging import get_logger
from app.services.media.progress import ProgressEvent, parse_progress_block

LOG = get_logger(__name__)


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
) -> CommandResult:
    """Run a command without a shell, streaming ``-progress`` blocks to ``on_progress``."""
    LOG.info("media.command.start", argv=[str(part) for part in args])
    process = subprocess.Popen(
        [str(part) for part in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    timed_out = threading.Event()

    def _kill_on_timeout() -> None:
        timed_out.set()
        process.kill()

    timer = threading.Timer(timeout, _kill_on_timeout) if timeout else None
    if timer is not None:
        timer.daemon = True
        timer.start()

    block: list[str] = []
    stdout_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        stdout_lines.append(line)
        if on_progress is not None:
            block.append(line)
            if line.startswith("progress="):
                event = parse_progress_block("".join(block), total_seconds)
                block.clear()
                if event is not None:
                    on_progress(event)
    stderr = process.stderr.read() if process.stderr is not None else ""
    process.stdout.close()
    if process.stderr is not None:
        process.stderr.close()
    if timer is not None:
        timer.cancel()

    returncode = process.wait()
    if timed_out.is_set():
        LOG.error("media.command.timeout", argv=[str(part) for part in args], timeout=timeout)
        msg = f"command timed out after {timeout}s"
        raise TimeoutError(msg)

    if returncode != 0:
        LOG.error("media.command.failed", returncode=returncode, stderr=stderr[-2000:])
        raise CommandFailedError(args, returncode, stderr)

    LOG.info("media.command.done", returncode=returncode)
    return CommandResult(returncode=returncode, stdout="".join(stdout_lines), stderr=stderr)
