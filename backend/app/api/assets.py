"""Media asset endpoints: import (probe), list, delete, proxy and job polling."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.deps import SessionDep, SettingsDep
from app.logging import get_logger
from app.models import MediaAsset, Project
from app.schemas_media import AssetCreate, AssetRead, EncoderProbe, JobRead
from app.services.media.jobs import JobRegistry
from app.services.media.service import MediaService, needs_proxy

router = APIRouter(tags=["media"])
LOG = get_logger(__name__)


def _media_service(request: Request) -> MediaService:
    service: MediaService = request.app.state.media_service
    return service


def _jobs(request: Request) -> JobRegistry:
    registry: JobRegistry = request.app.state.jobs
    return registry


def _project_or_404(session: SessionDep, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _asset_or_404(session: SessionDep, asset_id: str) -> MediaAsset:
    asset = session.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.post(
    "/projects/{project_id}/assets",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import a media file",
)
def import_asset(
    project_id: str,
    payload: AssetCreate,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> MediaAsset:
    """Probe a local file and register it as an asset (never copies the file)."""
    _project_or_404(session, project_id)
    path = Path(payload.path).expanduser()
    try:
        info = _media_service(request).probe(path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except Exception as error:
        LOG.error("media.probe.unavailable", path=str(path), error=str(error))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ffprobe unavailable: {error}",
        ) from error

    existing = (
        session.query(MediaAsset).filter_by(project_id=project_id, path=str(path)).one_or_none()
    )
    if existing is not None:
        return existing

    asset = MediaAsset(
        project_id=project_id,
        path=str(path),
        role=payload.role,
        kind="video" if info.video_codec else "audio",
        duration=info.duration,
        fps=info.fps,
        width=info.width,
        height=info.height,
        probe_json=_safe_dump(info.raw),
    )
    session.add(asset)
    session.flush()
    LOG.info("media.imported", project_id=project_id, asset_id=asset.id, role=asset.role)
    _ = settings
    return asset


def _safe_dump(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)[:20000]


@router.get("/projects/{project_id}/assets", response_model=list[AssetRead], summary="List assets")
def list_assets(project_id: str, session: SessionDep) -> list[MediaAsset]:
    _project_or_404(session, project_id)
    return list(
        session.query(MediaAsset).filter_by(project_id=project_id).order_by(MediaAsset.created_at)
    )


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove asset",
)
def delete_asset(asset_id: str, session: SessionDep) -> Response:
    session.delete(_asset_or_404(session, asset_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/assets/{asset_id}/proxy", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED
)
def make_proxy(
    asset_id: str, request: Request, session: SessionDep, settings: SettingsDep
) -> JobRead:
    """Queue a proxy render; returns the job so the UI can show real progress."""
    asset = _asset_or_404(session, asset_id)
    source = Path(asset.path)
    registry = _jobs(request)
    job = registry.create("proxy")
    service = _media_service(request)

    def worker() -> None:
        registry.update(job.id, state="running", percent=0, message="analysing")
        try:
            info = service.probe(source)
            if not needs_proxy(info):
                registry.update(job.id, state="done", percent=100, message="proxy not required")
                return
            out_dir = settings.cache_dir / "proxies"
            out_dir.mkdir(parents=True, exist_ok=True)
            from app.services.media.runner import run_command

            run_command(service.proxy_plan(source, info, out_dir), timeout=None)
            registry.update(job.id, state="done", percent=100, message="proxy ready")
        except Exception as error:
            LOG.error("media.proxy.failed", asset_id=asset.id, error=str(error))
            registry.update(job.id, state="failed", error=str(error), message="proxy failed")

    threading.Thread(target=worker, name=f"proxy-{job.id}", daemon=True).start()
    return JobRead.model_validate(job, from_attributes=True)


@router.get("/jobs", response_model=list[JobRead], summary="List jobs")
def list_jobs(request: Request) -> list[JobRead]:
    return [JobRead.model_validate(job, from_attributes=True) for job in _jobs(request).list()]


@router.get("/jobs/{job_id}", response_model=JobRead, summary="Job state")
def get_job(job_id: str, request: Request) -> JobRead:
    job = _jobs(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job, from_attributes=True)


@router.get("/media/encoder", response_model=EncoderProbe, summary="Detect H.264 encoder")
def detect_encoder(request: Request) -> EncoderProbe:
    """NVENC on the owner's GTX 1650, openh264 otherwise (never libx264)."""
    encoder = _media_service(request).detect_h264_encoder()
    return EncoderProbe(
        encoder=encoder,
        hardware=encoder == "h264_nvenc",
        note="NVENC H.264 only (no AV1/B-frames on Turing)"
        if encoder == "h264_nvenc"
        else "software/openh264 path",
    )
