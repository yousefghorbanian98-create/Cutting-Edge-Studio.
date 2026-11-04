"""In-memory job registry for long-running media work.

Local-only by design: no queue server, no network. Jobs are polled by the UI through
``GET /api/v1/jobs`` and their progress is mirrored into the log file.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.logging import get_logger

LOG = get_logger(__name__)

JobState = Literal["queued", "running", "done", "failed", "cancelled"]


@dataclass
class Job:
    """A unit of background work (proxy render, analysis pass, export)."""

    id: str
    kind: str
    state: JobState = "queued"
    percent: float = 0.0
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    error: str | None = None
    project_id: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)


class JobRegistry:
    """Thread-safe registry (FFmpeg runs in a worker thread, the API in another)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, *, project_id: str | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, project_id=project_id)
        with self._lock:
            self._jobs[job.id] = job
        LOG.info("job.created", job_id=job.id, kind=kind)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def update(
        self,
        job_id: str,
        *,
        state: JobState | None = None,
        percent: float | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if state is not None:
                job.state = state
            if percent is not None:
                job.percent = max(0.0, min(100.0, percent))
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            job.updated_at = datetime.now(tz=UTC)
            return job
