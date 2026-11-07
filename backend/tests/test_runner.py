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


def test_large_stderr_does_not_deadlock_stdout_reader() -> None:
    result = run_command(python("import sys; sys.stderr.write('x'*200000); print('ok')"), timeout=5)
    assert result.stdout.strip() == "ok"
    from app.services.media.runner import MAX_STDERR_BYTES

    assert len(result.stderr) == MAX_STDERR_BYTES


def test_cancellation_kills_and_reaps_child() -> None:
    import threading
    import time

    from app.services.media.runner import CommandCancelledError

    cancel = threading.Event()
    timer = threading.Timer(0.15, cancel.set)
    timer.start()
    start = time.monotonic()
    try:
        with pytest.raises(CommandCancelledError):
            run_command(python("import time; time.sleep(20)"), timeout=5, cancel_event=cancel)
    finally:
        timer.cancel()
        timer.join()
    assert time.monotonic() - start < 3


def test_cancelled_command_does_not_spawn(monkeypatch) -> None:
    import threading

    from app.services.media.runner import CommandCancelledError

    cancel = threading.Event()
    cancel.set()

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("A cancelled task must not spawn a child")

    monkeypatch.setattr("app.services.media.runner.subprocess.Popen", forbidden)
    with pytest.raises(CommandCancelledError):
        run_command(python("print('bad')"), cancel_event=cancel)


def test_callback_failure_still_reaps_child() -> None:
    import time

    def fail(_event: ProgressEvent) -> None:
        raise ValueError("callback failure")

    script = (
        "import time; print('out_time=00:00:01\\nprogress=continue',flush=True); time.sleep(20)"
    )
    start = time.monotonic()
    with pytest.raises(ValueError, match="callback failure"):
        run_command(python(script), timeout=5, on_progress=fail)
    assert time.monotonic() - start < 3


def test_stdout_limit_kills_child_without_retaining_unbounded_output(monkeypatch) -> None:
    monkeypatch.setattr("app.services.media.runner.MAX_STDOUT_CHARS", 4096)
    with pytest.raises(RuntimeError, match="safety limit"):
        run_command(
            python(
                "import sys,time; sys.stdout.write('x'*5000); sys.stdout.flush(); time.sleep(20)"
            ),
            timeout=5,
        )


def test_non_utf8_stderr_is_preserved_as_replacement_not_a_crash() -> None:
    result = run_command(python("import sys; sys.stderr.buffer.write(bytes([255]))"), timeout=5)
    assert result.stderr == "\ufffd"
