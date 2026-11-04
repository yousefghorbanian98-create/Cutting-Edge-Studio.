"""Local measurements using existing FFmpeg/progress/job/SQLite infrastructure.

This is NOT the model-driven Style Match pipeline. No supplied labels, synthetic DNA,
model downloads or video encoders are used. Completed reports are stored in existing artifacts.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from os import stat_result
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.logging import get_logger
from app.models import Artifact, MediaAsset
from app.schemas_inspection import (
    InspectedFile,
    InspectionRead,
    InspectionReport,
    InspectionRequest,
    Operation,
)
from app.schemas_media import AssetRead
from app.schemas_rhythm import RhythmFile, RhythmReport
from app.schemas_scenes import SceneFile, SceneReport
from app.services.media.ffmpeg import FFmpegBinaries, probe_command, resolve_binaries
from app.services.media.jobs import Job, JobRegistry
from app.services.media.probe import parse_probe
from app.services.media.progress import ProgressEvent
from app.services.media.runner import CommandCancelledError, run_command

LOG = get_logger(__name__)
KIND = "media-inspection"
ACTIVE = {"queued", "running"}


def operation_kind(operation: Operation) -> str:
    return {"decode": KIND, "rhythm": "audio-rhythm", "scenes": "shot-candidates"}[operation]


def hash_input(path: Path, cancel: threading.Event) -> str:
    """Hash original bytes with cooperative cancellation/deadline checks between reads."""
    digest = hashlib.sha256()
    deadline = time.monotonic() + 60
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            if cancel.is_set():
                raise CommandCancelledError("Media task cancelled")
            if time.monotonic() > deadline:
                raise TimeoutError("Media hashing exceeded its 60 second limit")
            digest.update(chunk)
    return digest.hexdigest()


def require_unchanged(path: Path, before: stat_result, name: str) -> stat_result:
    """Reject changed input identity instead of attaching measurements to new bytes."""
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValueError(f"Input changed during inspection: {name}; run again")
    return after


class InspectionBusyError(RuntimeError):
    """Only one local measurement worker is allowed at a time."""


class Inspector(Protocol):
    """Injectable OSS measurement boundary; tests can supply an explicit fixture."""

    def inspect(
        self, asset: AssetRead, cancel: threading.Event, progress: Callable[[float], None]
    ) -> InspectedFile | RhythmFile | SceneFile:
        """Measure the actual asset, or raise on cancellation/failure."""


def decode_command(binaries: FFmpegBinaries, path: Path) -> list[str]:
    """Decode first video/audio streams to a null sink, never an H.264 export."""
    return [
        str(binaries.ffmpeg),
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-v",
        "error",
        "-xerror",
        "-progress",
        "pipe:1",
        "-threads",
        "1",
        "-i",
        str(path),
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
        "-sn",
        "-dn",
        "-threads",
        "1",
        "-f",
        "null",
        "-",
    ]


class FFmpegInspector:
    """ffprobe metadata, content hash and full FFmpeg decode with cancellable progress."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def inspect(
        self, asset: AssetRead, cancel: threading.Event, progress: Callable[[float], None]
    ) -> InspectedFile:
        """Do not report success for metadata alone or when bytes change mid-inspection."""
        binaries = resolve_binaries(self.settings, allow_path_fallback=False)
        path = Path(asset.path)
        before = path.stat()
        digest = hash_input(path, cancel)
        info = parse_probe(
            run_command(probe_command(binaries, path), timeout=60, cancel_event=cancel).stdout
        )
        frames, seconds = 0, 0.0

        def measured(event: ProgressEvent) -> None:
            nonlocal frames, seconds
            frames = max(frames, event.frame)
            seconds = max(seconds, event.out_time_seconds)
            progress(min(99, event.percent or 0))

        run_command(
            decode_command(binaries, path),
            timeout=300,
            cancel_event=cancel,
            on_progress=measured,
            total_seconds=info.duration,
        )
        after = require_unchanged(path, before, asset.name)
        if info.video_codec and frames == 0:
            raise ValueError(f"No video frames decoded: {asset.name}")
        return InspectedFile(
            asset_id=asset.id,
            role=asset.role,
            name=asset.name,
            sha256=digest,
            size_bytes=after.st_size,
            mtime_ns=str(after.st_mtime_ns),
            duration=info.duration,
            width=info.width,
            height=info.height,
            fps=info.fps,
            video_codec=info.video_codec,
            audio_codec=info.audio_codec,
            has_audio=info.has_audio,
            decoded_frames=frames,
            decoded_seconds=seconds,
        )


class InspectionService:
    """One bounded worker, existing JobRegistry live progress, existing Artifact durability."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        jobs: JobRegistry,
        inspector: Inspector,
        rhythm_inspector: Inspector | None = None,
        scene_inspector: Inspector | None = None,
    ) -> None:
        self.factory, self.jobs, self.inspector = factory, jobs, inspector
        self.rhythm_inspector = rhythm_inspector
        self.scene_inspector = scene_inspector
        self.lock = threading.Lock()
        self.active: Job | None = None
        self.worker: threading.Thread | None = None

    def start(
        self,
        session: Session,
        project_id: str,
        payload: InspectionRequest,
        assets: list[AssetRead],
        *,
        operation: Operation = "decode",
    ) -> InspectionRead:
        """Commit the accepted job before starting any work; never queue unlimited decodes."""
        with self.lock:
            if self.active is not None and self.active.state in ACTIVE:
                raise InspectionBusyError(
                    "A media inspection is already running; wait or cancel it first"
                )
            kind = operation_kind(operation)
            job = self.jobs.create(kind, project_id=project_id)
            initial = InspectionRead(
                operation=operation,
                id=job.id,
                project_id=project_id,
                reference_asset_id=payload.reference_asset_id,
                source_asset_ids=payload.source_asset_ids,
                state="queued",
                message="Waiting for decoder",
            )
            try:
                session.add(
                    Artifact(
                        id=job.id,
                        project_id=project_id,
                        kind=kind,
                        revision=session.query(Artifact)
                        .filter_by(project_id=project_id, kind=kind)
                        .count()
                        + 1,
                        payload_json=initial.model_dump_json(),
                    )
                )
                session.commit()
                self.active = job
                self.worker = threading.Thread(
                    target=self._run,
                    args=(job, initial, assets),
                    daemon=True,
                    name=f"inspection-{job.id}",
                )
                self.worker.start()
            except Exception as error:
                session.rollback()
                self.jobs.update(
                    job.id, state="failed", error=str(error), message="Could not start inspection"
                )
                LOG.error("inspection.start.failed", project_id=project_id, error=str(error))
                raise
            return initial

    def _persist(self, result: InspectionRead) -> None:
        with self.factory() as session:
            row = session.get(Artifact, result.id)
            if row is None:
                raise FileNotFoundError("Inspection project/job was deleted")
            row.payload_json = result.model_dump_json()
            session.commit()

    def _finish(
        self,
        job: Job,
        initial: InspectionRead,
        state: str,
        error: str | None = None,
        report: InspectionReport | RhythmReport | SceneReport | None = None,
    ) -> None:
        result = initial.model_copy(
            update={
                "state": state,
                "percent": 100 if state == "done" else job.percent,
                "message": "Measurements saved; model analysis not performed"
                if state == "done"
                else state,
                "error": error,
                "report": report,
            }
        )
        try:
            self._persist(result)
        except Exception as persistence_error:
            LOG.error("inspection.persist.failed", job_id=job.id, error=str(persistence_error))
            self.jobs.update(
                job.id,
                state="failed",
                error=f"Could not save inspection: {persistence_error}",
                message="Inspection not saved",
            )
        else:
            self.jobs.update(
                job.id, state=state, percent=result.percent, error=error, message=result.message
            )

    def _inspector(self, operation: Operation) -> Inspector:
        inspector = {
            "decode": self.inspector,
            "rhythm": self.rhythm_inspector,
            "scenes": self.scene_inspector,
        }[operation]
        if inspector is None:
            raise RuntimeError(f"{operation} processor is not configured")
        return inspector

    def _run(self, job: Job, initial: InspectionRead, assets: list[AssetRead]) -> None:
        try:
            self.jobs.update(job.id, state="running", message="Hashing and probing input files")
            files = []
            for index, asset in enumerate(assets):
                _check_cancel(job)
                self.jobs.update(
                    job.id, message=f"Inspecting {index+1}/{len(assets)}: {asset.name}"
                )

                def progress(percent: float, index: int = index) -> None:
                    self.jobs.update(
                        job.id, percent=min(99, 100 * (index + percent / 100) / len(assets))
                    )

                inspector = self._inspector(initial.operation)
                files.append(inspector.inspect(asset, job.cancel_event, progress))
                self.jobs.update(job.id, percent=min(99, 100 * (index + 1) / len(assets)))
            report = {"decode": InspectionReport, "rhythm": RhythmReport, "scenes": SceneReport}[
                initial.operation
            ](files=files)
            with self.lock:
                _check_cancel(job)
                with self.factory() as session:
                    self._validate_report(session, report)
                self._finish(job, initial, "done", report=report)
        except CommandCancelledError as error:
            LOG.info("inspection.cancelled", job_id=job.id)
            self._finish(job, initial, "cancelled", error=str(error))
        except Exception as error:
            LOG.error("inspection.failed", job_id=job.id, error=str(error))
            self._finish(job, initial, "failed", error=str(error))

    def _validate_report(
        self, session: Session, report: InspectionReport | RhythmReport | SceneReport
    ) -> None:
        if self._stale(session, report):
            raise ValueError("Inspection inputs changed or were deleted; run again")

    def _stale(
        self, session: Session, report: InspectionReport | RhythmReport | SceneReport
    ) -> bool:
        rows = {
            row.id: row
            for row in session.scalars(
                select(MediaAsset).where(MediaAsset.id.in_([f.asset_id for f in report.files]))
            )
        }
        for measured in report.files:
            row = rows.get(measured.asset_id)
            if row is None or row.role != measured.role:
                return True
            try:
                current = Path(row.path).stat()
            except OSError as error:
                LOG.warning(
                    "inspection.input.unavailable", asset_id=measured.asset_id, error=str(error)
                )
                return True
            if (current.st_size, str(current.st_mtime_ns)) != (
                measured.size_bytes,
                measured.mtime_ns,
            ):
                return True
        return False

    def read(
        self,
        session: Session,
        project_id: str,
        job_id: str | None = None,
        *,
        operation: Operation = "decode",
    ) -> InspectionRead:
        """Recover terminal reports, and explicitly mark jobs interrupted by backend restart."""
        with self.lock:
            query = select(Artifact).where(
                Artifact.project_id == project_id, Artifact.kind == operation_kind(operation)
            )
            query = (
                query.where(Artifact.id == job_id)
                if job_id
                else query.order_by(Artifact.created_at.desc()).limit(1)
            )
            row = session.scalars(query).first()
            if row is None:
                raise FileNotFoundError("No media inspection found for this project")
            record = InspectionRead.model_validate_json(row.payload_json)
            if (record.id, record.project_id, record.operation) != (row.id, project_id, operation):
                raise ValueError(
                    "Stored measurement identity or operation does not match its artifact"
                )
            live = self.jobs.get(record.id)
            if live is not None:
                record = record.model_copy(
                    update={
                        "state": live.state,
                        "percent": live.percent,
                        "message": live.message,
                        "error": live.error,
                    }
                )
            elif record.state in ACTIVE:
                record = record.model_copy(
                    update={
                        "state": "interrupted",
                        "error": "Backend restarted before inspection finished; run again",
                        "message": "Inspection interrupted",
                    }
                )
                row.payload_json = record.model_dump_json()
                session.commit()
                LOG.warning("inspection.interrupted", job_id=record.id)
            if record.report:
                record.stale = self._stale(session, record.report)
            return record

    def cancel(
        self, session: Session, project_id: str, job_id: str, *, operation: Operation = "decode"
    ) -> InspectionRead:
        """Request cancellation without fabricating terminal success."""
        record = self.read(session, project_id, job_id, operation=operation)
        with self.lock:
            job = self.jobs.get(job_id)
            if job is not None and job.state in ACTIVE:
                job.cancel_event.set()
                self.jobs.update(job_id, message="Cancellation requested; stopping decoder")
        return record

    def shutdown(self) -> None:
        """Stop/reap the worker before disposing the app's DB engine."""
        if self.active is not None:
            self.active.cancel_event.set()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=5)
            if self.worker.is_alive():
                LOG.error(
                    "inspection.shutdown.timeout", job_id=self.active.id if self.active else None
                )


def _check_cancel(job: Job) -> None:
    if job.cancel_event.is_set():
        raise CommandCancelledError("Media inspection cancelled")
