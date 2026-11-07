"""Isolated, cancellable-by-parent librosa entry point; no server or model downloads."""

from __future__ import annotations

import argparse
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

import psutil

from app.logging import get_logger
from app.schemas_rhythm import RhythmEstimate
from app.services.audio.rhythm import analyze_pcm_wav

LOG = get_logger(__name__)

LIFETIME_SECONDS = 185


@contextmanager
def parent_lifetime() -> Iterator[None]:
    """Reuse psutil to stop an isolated worker if its launching backend disappears.

    The parent still enforces the normal 180 second deadline. This independent
    guard is for parent crashes, not a Windows packaged-runtime certification.
    """
    expected_pid = os.environ.get("CE_RHYTHM_PARENT_PID")
    if expected_pid is None:  # Standalone CLI/library tests, outside project jobs.
        yield
        return
    parent = psutil.Process(int(expected_pid))
    if parent.create_time() != float(os.environ["CE_RHYTHM_PARENT_CREATED"]):
        raise RuntimeError("Rhythm worker parent identity changed")
    stopped = threading.Event()
    deadline = time.monotonic() + LIFETIME_SECONDS

    def monitor() -> None:
        while not stopped.wait(0.1):
            try:
                healthy = parent.is_running() and parent.status() != psutil.STATUS_ZOMBIE
            except psutil.Error as error:
                try:
                    LOG.error("audio.worker.parent_check.failed", error=str(error))
                finally:
                    psutil.Process().kill()
                return
            if not healthy or time.monotonic() > deadline:
                try:
                    LOG.error("audio.worker.lifetime_ended", parent_alive=healthy)
                finally:  # A dead parent's closed stdout must not prevent termination.
                    psutil.Process().kill()
                return

    watcher = threading.Thread(target=monitor, daemon=True, name="rhythm-parent-watch")
    watcher.start()
    try:
        yield
    finally:
        stopped.set()
        watcher.join(timeout=1)


def worker_main(argv: list[str] | None = None) -> None:
    """Write validated JSON only after actual PCM analysis, then exit the child."""
    parser = argparse.ArgumentParser(description="Internal local rhythm measurement worker")
    parser.add_argument("wav", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args(argv)
    try:
        with parent_lifetime():
            measured = RhythmEstimate.model_validate(asdict(analyze_pcm_wav(args.wav)))
            args.result.write_text(measured.model_dump_json(), encoding="utf-8")
    except Exception as error:
        LOG.error("audio.worker.failed", error=str(error))
        raise


if __name__ == "__main__":
    worker_main()
