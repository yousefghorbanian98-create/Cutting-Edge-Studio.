"""FFmpeg -progress parsing and job registry."""

from __future__ import annotations

from app.services.media.jobs import JobRegistry
from app.services.media.progress import parse_progress_block

BLOCK = """frame=120
fps=60.0
out_time=00:00:04.000000
speed=2.5x
progress=continue
"""

END_BLOCK = """frame=300
out_time=00:00:10.000000
speed=3.0x
progress=end
"""


def test_parses_progress_block_with_total() -> None:
    event = parse_progress_block(BLOCK, total_seconds=20)
    assert event is not None
    assert event.out_time_seconds == 4.0
    assert event.speed == 2.5
    assert event.frame == 120
    assert event.percent == 20.0
    assert event.done is False


def test_final_block_is_always_100_percent() -> None:
    event = parse_progress_block(END_BLOCK, total_seconds=99)
    assert event is not None
    assert event.done is True
    assert event.percent == 100.0


def test_unknown_total_yields_no_percent() -> None:
    event = parse_progress_block(BLOCK)
    assert event is not None
    assert event.percent is None


def test_empty_block_is_ignored() -> None:
    assert parse_progress_block("") is None
    assert parse_progress_block("\n\n") is None


def test_job_registry_lifecycle() -> None:
    registry = JobRegistry()
    job = registry.create("proxy")
    assert registry.get(job.id) is job
    assert job.state == "queued"

    registry.update(job.id, state="running", percent=42, message="encoding")
    assert registry.get(job.id).percent == 42.0

    registry.update(job.id, percent=250)
    assert registry.get(job.id).percent == 100.0

    registry.update(job.id, state="failed", error="boom")
    assert registry.get(job.id).error == "boom"
    assert [item.id for item in registry.list()] == [job.id]
    assert registry.get("missing") is None
    assert registry.update("missing", percent=1) is None
