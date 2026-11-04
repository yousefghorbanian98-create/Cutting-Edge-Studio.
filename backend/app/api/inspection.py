"""Real-media inspection orchestration, not fixture-driven Style Match analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.assets import _to_read
from app.deps import SessionDep, SettingsDep
from app.logging import get_logger
from app.models import MediaAsset, Project
from app.schemas_inspection import InspectionRead, InspectionRequest
from app.services.media.ffmpeg import FFmpegNotFoundError, resolve_binaries
from app.services.media.inspection import InspectionBusyError, InspectionService

router = APIRouter(prefix="/projects/{project_id}/inspection", tags=["media-inspection"])
LOG = get_logger(__name__)


def _project(session: SessionDep, project_id: str) -> None:
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _service(request: Request) -> InspectionService:
    return request.app.state.inspection


@router.get("/capabilities")
def capabilities(project_id: str, session: SessionDep, settings: SettingsDep) -> dict[str, object]:
    """Existence of local weights is not advertised as working inference."""
    _project(session, project_id)
    reason = None
    try:
        resolve_binaries(settings, allow_path_fallback=False)
    except FFmpegNotFoundError as error:
        LOG.warning("inspection.tools.unavailable", error=str(error))
        reason = str(error)
    return {
        "inspection": {"available": reason is None, "reason": reason},
        "model_analysis": {
            "available": False,
            "reason": (
                "Verified pretrained weights and wired inference adapters are required. "
                "Configure pinned local models on the build machine; "
                "no runtime downloads are performed."
            ),
            "unavailable": ["beats", "shot boundaries", "pose/action inference", "StyleDNA", "EDL"],
            "models_directory": str(settings.home_dir / "models"),
        },
    }


@router.post("/jobs", response_model=InspectionRead, status_code=202)
def start(
    project_id: str,
    payload: InspectionRequest,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> InspectionRead:
    """Resolve all inputs inside this project, then start one bounded decode worker."""
    _project(session, project_id)
    ids = [payload.reference_asset_id, *payload.source_asset_ids]
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status_code=422, detail="Reference/source IDs must be distinct and unique"
        )
    rows = list(
        session.scalars(
            select(MediaAsset).where(MediaAsset.project_id == project_id, MediaAsset.id.in_(ids))
        )
    )
    by_id = {row.id: row for row in rows}
    if any(asset_id not in by_id for asset_id in ids):
        raise HTTPException(status_code=422, detail="Input asset is not registered in this project")
    assets = [_to_read(by_id[asset_id]) for asset_id in ids]
    if assets[0].role != "reference" or any(a.role != "source" for a in assets[1:]):
        raise HTTPException(status_code=422, detail="Choose an explicit reference and source clips")
    if any(not a.available or a.duration <= 0 for a in assets):
        raise HTTPException(
            status_code=422, detail="Input media is unavailable or has no usable duration"
        )
    try:
        resolve_binaries(settings, allow_path_fallback=False)
        return _service(request).start(session, project_id, payload, assets)
    except InspectionBusyError as error:
        LOG.warning("inspection.busy", project_id=project_id, error=str(error))
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        LOG.error("inspection.start.unavailable", project_id=project_id, error=str(error))
        raise HTTPException(
            status_code=503, detail=f"Cannot start media inspection: {error}"
        ) from error


@router.get("/latest", response_model=InspectionRead)
def latest(project_id: str, request: Request, session: SessionDep) -> InspectionRead:
    """Recover the latest accepted job/report after UI or backend restart."""
    return get_job(project_id, None, request, session)


@router.get("/jobs/{job_id}", response_model=InspectionRead)
def get_job(
    project_id: str, job_id: str | None, request: Request, session: SessionDep
) -> InspectionRead:
    """Jobs cannot be read through another project's route."""
    _project(session, project_id)
    try:
        return _service(request).read(session, project_id, job_id)
    except FileNotFoundError as error:
        LOG.warning("inspection.not_found", project_id=project_id, error=str(error))
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        LOG.error("inspection.read.failed", project_id=project_id, error=str(error))
        raise HTTPException(status_code=503, detail=f"Cannot read inspection: {error}") from error


@router.post("/jobs/{job_id}/cancel", response_model=InspectionRead)
def cancel(project_id: str, job_id: str, request: Request, session: SessionDep) -> InspectionRead:
    """Request cancellation; the worker stops the child before reporting cancelled."""
    _project(session, project_id)
    try:
        return _service(request).cancel(session, project_id, job_id)
    except FileNotFoundError as error:
        LOG.warning("inspection.cancel.not_found", project_id=project_id, error=str(error))
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        LOG.error("inspection.cancel.failed", project_id=project_id, error=str(error))
        raise HTTPException(status_code=503, detail=f"Cannot cancel inspection: {error}") from error
