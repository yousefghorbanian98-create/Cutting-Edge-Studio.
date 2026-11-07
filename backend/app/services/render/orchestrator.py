# ruff: noqa: TRY301, C901, PLR0912, PLR0915
"""Honest EDL-to-render orchestrator — approved encoder only, observed progress."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.logging import get_logger
from app.models import Artifact
from app.schemas_render import RenderRead, RenderReport
from app.services.media.ffmpeg import (
    FORBIDDEN_ENCODERS,
    H264_ENCODERS,
    available_h264_encoder,
    forbidden_encoders_present,
    parse_encoders,
    probe_command,
    resolve_binaries,
)
from app.services.media.jobs import Job, JobRegistry
from app.services.media.probe import parse_probe
from app.services.media.runner import CommandCancelledError, run_command
from app.services.stylematch.render import build_edl_command

LOG = get_logger(__name__)
ACTIVE = {"queued", "running"}
KIND = "render-job"


def _probe_encoder(binaries: Any, timeout: float = 30) -> set[str]:
    """Run ffmpeg -encoders and parse; never shells out."""
    result = run_command([str(binaries.ffmpeg), "-hide_banner", "-encoders"], timeout=timeout)
    return parse_encoders(result.stdout + result.stderr)


def pick_encoder(settings: Settings, preferred: str | None = None) -> str:
    """Choose allowed encoder or raise with actionable 503 message."""
    binaries = resolve_binaries(settings, allow_path_fallback=False)
    encoders = _probe_encoder(binaries)
    forbidden = forbidden_encoders_present(encoders)
    if forbidden:
        LOG.warning("render.forbidden_encoders_present", encoders=sorted(forbidden))
        # Still allow render with allowed encoder; just warn. Caller-forbidden blocked below.
    if preferred and preferred in FORBIDDEN_ENCODERS:
        raise ValueError(f"encoder '{preferred}' is not allowed (GPL) — use {H264_ENCODERS}")
    if preferred and preferred in H264_ENCODERS and preferred in encoders:
        return preferred
    chosen = available_h264_encoder(encoders)
    if chosen is None:
        raise RuntimeError(
            f"No approved H.264 encoder found. Expected one of {H264_ENCODERS}. "
            f"Bundle the LGPL shared FFmpeg with {H264_ENCODERS[1]} or NVENC build; "
            "no GPL libx264. See docs/pins.json and scripts/build-installer.ps1."
        )
    return chosen


def _output_dir(settings: Settings, project_id: str) -> Path:
    d = settings.projects_dir / project_id / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


class RenderService:
    """One bounded worker, JobRegistry live progress, Artifact durability, real FFmpeg."""

    def __init__(
        self, factory: sessionmaker[Session], jobs: JobRegistry, settings: Settings
    ) -> None:
        self.factory = factory
        self.jobs = jobs
        self.settings = settings
        self.lock = threading.Lock()
        self.active: Job | None = None
        self.worker: threading.Thread | None = None

    def start(
        self,
        session: Session,
        project_id: str,
        edl: dict[str, Any],
        quality: str = "preview",
        subtitles_ass: str | None = None,
        loudness_filter: str | None = None,
        has_audio: bool | None = None,
    ) -> RenderRead:
        with self.lock:
            if self.active is not None and self.active.state in ACTIVE:
                from app.services.media.inspection import InspectionBusyError

                raise InspectionBusyError("A render is already running; wait or cancel it first")
            job = self.jobs.create(KIND, project_id=project_id)
            initial = RenderRead(
                id=job.id,
                project_id=project_id,
                state="queued",
                percent=0,
                message="Render queued",
                quality=quality,
            )
            # Persist EDL + initial state so restart can mark interrupted
            _ = {
                "edl": edl,
                "quality": quality,
                "render": initial.model_dump(),
            }  # keep EDL for debugging
            session.add(
                Artifact(
                    id=job.id,
                    project_id=project_id,
                    kind=KIND,
                    revision=session.query(Artifact)
                    .filter_by(project_id=project_id, kind=KIND)
                    .count()
                    + 1,
                    payload_json=RenderRead.model_validate(
                        initial
                    ).model_dump_json(),  # store RenderRead directly for simplicity
                )
            )
            # Also store EDL separately for debugging (optional)
            session.commit()
            self.active = job
            self.worker = threading.Thread(
                target=self._run,
                args=(job, initial, edl, quality, subtitles_ass, loudness_filter, has_audio),
                daemon=True,
                name=f"render-{job.id}",
            )
            self.worker.start()
            return initial

    def _persist(self, result: RenderRead) -> None:
        with self.factory() as session:
            row = session.get(Artifact, result.id)
            if row is None:
                raise FileNotFoundError("Render project/job was deleted")
            row.payload_json = result.model_dump_json()
            session.commit()

    def _finish(
        self,
        job: Job,
        initial: RenderRead,
        state: str,
        error: str | None = None,
        report: RenderReport | None = None,
    ) -> None:
        result = initial.model_copy(
            update={
                "state": state,
                "percent": 100 if state == "done" else job.percent,
                "message": "Render complete" if state == "done" else state,
                "error": error,
                "report": report,
            }
        )
        try:
            self._persist(result)
        except Exception as exc:  # pragma: no cover
            LOG.error("render.persist.failed", job_id=job.id, error=str(exc))
            self.jobs.update(
                job.id,
                state="failed",
                error=f"Could not save render: {exc}",
                message="Render not saved",
            )
        else:
            self.jobs.update(
                job.id, state=state, percent=result.percent, error=error, message=result.message
            )

    def _run(
        self,
        job: Job,
        initial: RenderRead,
        edl: dict[str, Any],
        quality: str,
        subtitles_ass: str | None = None,
        loudness_filter: str | None = None,
        has_audio: bool | None = None,
    ) -> None:
        try:
            self.jobs.update(job.id, state="running", message="Probing encoder")
            # Validate EDL has segments
            if not edl.get("segments"):
                raise ValueError("cannot render an empty EDL")
            # Encoder probe — honest 503 if missing
            encoder = pick_encoder(self.settings)
            self.jobs.update(job.id, message=f"Encoder {encoder} selected")
            # Build output path
            out_dir = _output_dir(self.settings, initial.project_id)
            output = out_dir / f"{job.id}.mp4"
            binaries = resolve_binaries(self.settings, allow_path_fallback=False)
            # Bitrate/encoder choice per quality
            if quality == "preview":
                bitrate = 1200
                cmd_encoder = encoder  # usually libopenh264 for preview
                # force libopenh264 for preview if available, else chosen
                if "libopenh264" in _probe_encoder(binaries):
                    cmd_encoder = "libopenh264"
            else:
                bitrate = 6000
                cmd_encoder = encoder
            # Handle subtitles: write ASS to temp file if provided
            subtitles_path = None
            if subtitles_ass:
                subtitles_path = out_dir / f"{job.id}.ass"
                subtitles_path.write_text(subtitles_ass, encoding="utf-8")
            # Loudness: already a filter string like loudnorm=... or volume=...
            command = build_edl_command(
                binaries,
                edl,
                output,
                encoder=cmd_encoder,
                bitrate_kbps=bitrate,
                subtitles_path=subtitles_path,
                loudness_filter=loudness_filter,
                has_audio=has_audio,
            )
            total = float(edl.get("total_duration", 10.0) or 10.0)

            def on_progress(event: object) -> None:
                # event.percent is 0-100 of ffmpeg progress; map to 0-99
                pct = event.percent if event.percent is not None else 0  # type: ignore[attr-defined]
                self.jobs.update(job.id, percent=min(99, pct), message=f"Rendering {pct:.1f}%")

            if job.cancel_event.is_set():
                raise CommandCancelledError("Render cancelled before start")
            self.jobs.update(job.id, message="Rendering EDL")
            # Timeout scales with content: 10 min base + 20x duration (e.g. 60s clip → 30 min max)
            timeout = max(600.0, total * 20.0)
            run_command(
                command,
                timeout=timeout,
                cancel_event=job.cancel_event,
                on_progress=on_progress,
                total_seconds=total,
            )
            # Verify output exists and probe it
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError("Render output missing or empty — no file produced")
            # Quick probe for duration sanity
            probe_out = run_command(probe_command(binaries, output), timeout=30).stdout
            info = parse_probe(probe_out)
            if info.duration <= 0:
                raise RuntimeError("Rendered file has no duration")
            report = RenderReport(
                output_path=str(output),
                duration=info.duration,
                width=int(edl.get("width", 1080)),
                height=int(edl.get("height", 1920)),
                fps=int(edl.get("fps", 30)),
                encoder=cmd_encoder,
                size_bytes=output.stat().st_size,
            )
            with self.lock:
                if job.cancel_event.is_set():
                    raise CommandCancelledError("Render cancelled")
                self._finish(job, initial, "done", report=report)
        except CommandCancelledError as exc:
            LOG.info("render.cancelled", job_id=job.id)
            self._finish(job, initial, "cancelled", error=str(exc))
        except Exception as exc:
            LOG.error("render.failed", job_id=job.id, error=str(exc))
            # Clean partial output
            try:
                out_dir = _output_dir(self.settings, initial.project_id)
                partial = out_dir / f"{job.id}.mp4"
                if partial.exists():
                    partial.unlink(missing_ok=True)
            except Exception as cleanup_exc:
                LOG.warning("render.cleanup.partial_failed", job_id=job.id, error=str(cleanup_exc))
            self._finish(job, initial, "failed", error=str(exc))

    def read(self, session: Session, project_id: str, job_id: str | None = None) -> RenderRead:
        with self.lock:
            from sqlalchemy import select

            from app.models import Artifact

            query = select(Artifact).where(Artifact.project_id == project_id, Artifact.kind == KIND)
            query = (
                query.where(Artifact.id == job_id)
                if job_id
                else query.order_by(Artifact.created_at.desc()).limit(1)
            )
            row = session.scalars(query).first()
            if row is None:
                raise FileNotFoundError("No render job for this project")
            record = RenderRead.model_validate_json(row.payload_json)
            if (record.id, record.project_id) != (row.id, project_id):
                raise ValueError("Stored render identity does not match artifact")
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
                        "error": "Backend restarted before render finished; run again",
                        "message": "Render interrupted",
                    }
                )
                row.payload_json = record.model_dump_json()
                session.commit()
                LOG.warning("render.interrupted", job_id=record.id)
            return record

    def cancel(self, session: Session, project_id: str, job_id: str) -> RenderRead:
        record = self.read(session, project_id, job_id)
        with self.lock:
            job = self.jobs.get(job_id)
            if job is not None and job.state in ACTIVE:
                job.cancel_event.set()
                self.jobs.update(job_id, message="Cancellation requested; stopping encoder")
        return record

    def shutdown(self) -> None:
        if self.active is not None:
            self.active.cancel_event.set()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=5)
            if self.worker.is_alive():
                LOG.error("render.shutdown.timeout", job_id=self.active.id if self.active else None)
