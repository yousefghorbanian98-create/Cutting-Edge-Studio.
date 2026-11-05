"""Real EDL-to-file render — approved encoder, honest errors, no GPL."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from app.deps import SessionDep, SettingsDep
from app.logging import get_logger
from app.models import Project
from app.schemas_render import RenderRead, RenderRequest
from app.services.media.ffmpeg import FFmpegNotFoundError, resolve_binaries
from app.services.media.inspection import InspectionBusyError
from app.services.render.orchestrator import pick_encoder

LOG = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/render", tags=["render"])


class EncoderRead(BaseModel):  # noqa: D101
    model_config = ConfigDict(extra="allow")
    encoder: str | None
    available_encoders: list[str]
    forbidden_present: list[str]
    note: str


def _project(session: SessionDep, project_id: str) -> None:
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/encoder", response_model=EncoderRead)
def encoder_probe(project_id: str, session: SessionDep, settings: SettingsDep) -> EncoderRead:
    _project(session, project_id)
    try:
        binaries = resolve_binaries(settings, allow_path_fallback=False)
        from app.services.media.ffmpeg import forbidden_encoders_present, parse_encoders
        from app.services.media.runner import run_command

        enc = set(
            parse_encoders(
                run_command([str(binaries.ffmpeg), "-hide_banner", "-encoders"], timeout=20).stdout
            )
        )
        from app.services.media.ffmpeg import H264_ENCODERS, available_h264_encoder

        chosen = available_h264_encoder(enc)
        forbidden = sorted(forbidden_encoders_present(enc))
        note = (
            "Approved encoders only: h264_nvenc or libopenh264 "
            "(LGPL). libx264 is GPL and never used."
        )
        if chosen is None:
            note = "No approved encoder found — bundle LGPL FFmpeg with libopenh264."
        return EncoderRead(
            encoder=chosen,
            available_encoders=sorted(enc.intersection(set(H264_ENCODERS))),
            forbidden_present=forbidden,
            note=note,
        )
    except FFmpegNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        LOG.error("render.encoder.failed", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/capabilities")
def capabilities(
    project_id: str, request: Request, session: SessionDep, settings: SettingsDep
) -> dict[str, Any]:
    _project(session, project_id)
    try:
        resolve_binaries(settings, allow_path_fallback=False)
        enc = pick_encoder(settings)
        available, reason = True, f"Encoder {enc} ready"
    except (FFmpegNotFoundError, RuntimeError, ValueError) as exc:
        available, reason = False, str(exc)
    return {
        "render": {"available": available, "reason": None if available else reason},
        "encoder": enc if available else None,
        "cache_recovery": request.app.state.cache_recovery,
    }


@router.post("/jobs", response_model=RenderRead, status_code=status.HTTP_202_ACCEPTED)
def start(
    project_id: str,
    payload: RenderRequest,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> RenderRead:
    _project(session, project_id)
    # Validate EDL quickly — must have segments
    edl = payload.edl
    if not edl.get("segments"):
        raise HTTPException(status_code=422, detail="EDL has no segments — build EDL first")
    # Encoder must be present before queueing
    try:
        resolve_binaries(settings, allow_path_fallback=False)
        pick_encoder(settings)
    except (FFmpegNotFoundError, RuntimeError, ValueError) as exc:
        LOG.warning("render.unavailable", project_id=project_id, error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        return request.app.state.render.start(session, project_id, edl, quality=payload.quality)
    except InspectionBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        LOG.error("render.start.failed", project_id=project_id, error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=RenderRead)
def read_job(project_id: str, job_id: str, request: Request, session: SessionDep) -> RenderRead:
    _project(session, project_id)
    try:
        return request.app.state.render.read(session, project_id, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/latest", response_model=RenderRead)
def latest(project_id: str, request: Request, session: SessionDep) -> RenderRead:
    _project(session, project_id)
    try:
        return request.app.state.render.read(session, project_id, None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/cancel", response_model=RenderRead)
def cancel(project_id: str, job_id: str, request: Request, session: SessionDep) -> RenderRead:
    _project(session, project_id)
    try:
        return request.app.state.render.cancel(session, project_id, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
