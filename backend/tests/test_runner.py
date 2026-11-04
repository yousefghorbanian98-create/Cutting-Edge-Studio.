"""Command runner: real subprocess execution without FFmpeg."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from app.services.media.progress import ProgressEvent
from app.services.media.runner import CommandFailedError, run_command


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_captures_stdout() -> None:
    result = run_command(python("print('hello')"), timeout=30)
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_streams_progress_blocks() -> None:
    events: list[ProgressEvent] = []
    script = (
        "import sys\n"
        "for i in (1, 2, 3):\n"
        "    sys.stdout.write(f'frame={i*10}\\nout_time=00:00:0{i}.000000\\nspeed=2.0x\\nprogress=continue\\n')\n"
        "    sys.stdout.flush()\n"
        "sys.stdout.write('progress=end\\n')\n"
    )
    run_command(python(script), timeout=30, on_progress=events.append, total_seconds=10)
    assert len(events) == 4
    assert events[0].frame == 10
    assert events[-1].done is True
    assert events[-1].percent == 100.0


def test_non_zero_exit_raises_with_stderr() -> None:
    with pytest.raises(CommandFailedError) as error:
        run_command(python("import sys; sys.stderr.write('bad things'); sys.exit(3)"), timeout=30)
    assert error.value.returncode == 3
    assert "bad things" in error.value.stderr_tail


def test_timeout_kills_the_process() -> None:
    with pytest.raises(TimeoutError):
        run_command(python("import time; time.sleep(5)"), timeout=0.3)


def test_runs_in_requested_cwd(tmp_path: Path) -> None:
    result = run_command(python("import os; print(os.getcwd())"), cwd=tmp_path, timeout=30)
    assert str(tmp_path) in result.stdout
