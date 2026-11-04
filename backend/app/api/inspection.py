"""Project-scoped decode/rhythm jobs sharing one existing durable worker and API flow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.assets import _to_read
from app.deps import SessionDep, SettingsDep
from app.logging import get_logger
from app.models import MediaAsset, Project
from app.schemas_inspection import InspectionRead, InspectionRequest, Operation
from app.schemas_media import AssetRead
from app.services.audio.processor import rhythm_unavailable
from app.services.media.ffmpeg import FFmpegNotFoundError, resolve_binaries
from app.services.media.inspection import InspectionBusyError
from app.services.media.scenes import scenes_unavailable

LOG = get_logger(__name__)


def _project(session: SessionDep, project_id: str) -> None:
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _assets(session: SessionDep, project_id: str, payload: InspectionRequest) -> list[AssetRead]:
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
    return assets


def _unavailable(settings: SettingsDep, operation: Operation) -> str | None:
    try:
        resolve_binaries(settings, allow_path_fallback=False)
    except FFmpegNotFoundError as error:
        LOG.warning("inspection.tools.unavailable", error=str(error))
        return str(error)
    if operation == "scenes":
        return scenes_unavailable(settings)
    return rhythm_unavailable(settings) if operation == "rhythm" else None


def _require_tools(settings: SettingsDep, operation: Operation) -> None:
    reason = _unavailable(settings, operation)
    if reason is not None:
        LOG.warning("inspection.operation.unavailable", operation=operation, reason=reason)
        raise HTTPException(status_code=503, detail=reason)


def _routes(operation: Operation) -> APIRouter:
    """Reuse existing request/identity/error semantics, without a second job framework."""
    path = {"decode": "inspection", "rhythm": "rhythm", "scenes": "scenes"}[operation]
    routes = APIRouter(prefix=f"/projects/{{project_id}}/{path}", tags=[path])

    @routes.get("/capabilities")
    def capabilities(
        project_id: str, request: Request, session: SessionDep, settings: SettingsDep
    ) -> dict[str, object]:
        _project(session, project_id)
        reason = _unavailable(settings, operation)
        return {
            "inspection": {"available": reason is None, "reason": reason},
            "operation": operation,
            "cache_recovery": request.app.state.cache_recovery,
            "model_analysis": {
                "available": False,
                "reason": (
                    "Verified pretrained weights and wired inference adapters are required. "
                    "Configure pinned local models on the build machine; "
                    "no runtime downloads are performed."
                ),
                "unavailable": ["shot boundaries", "pose/action inference", "StyleDNA", "EDL"],
                "models_directory": str(settings.home_dir / "models"),
            },
        }

    @routes.post("/jobs", response_model=InspectionRead, status_code=202)
    def start(
        project_id: str,
        payload: InspectionRequest,
        request: Request,
        session: SessionDep,
        settings: SettingsDep,
    ) -> InspectionRead:
        _project(session, project_id)
        assets = _assets(session, project_id, payload)
        _require_tools(settings, operation)
        try:
            return request.app.state.inspection.start(
                session, project_id, payload, assets, operation=operation
            )
        except InspectionBusyError as error:
            LOG.warning("inspection.busy", project_id=project_id, error=str(error))
            raise HTTPException(status_code=409, detail=str(error)) from error
        except Exception as error:
            LOG.error("inspection.start.unavailable", project_id=project_id, error=str(error))
            raise HTTPException(
                status_code=503, detail=f"Cannot start {operation}: {error}"
            ) from error

    def read_job(
        project_id: str, job_id: str | None, request: Request, session: SessionDep
    ) -> InspectionRead:
        _project(session, project_id)
        try:
            return request.app.state.inspection.read(
                session, project_id, job_id, operation=operation
            )
        except FileNotFoundError as error:
            LOG.warning("inspection.not_found", project_id=project_id, error=str(error))
            raise HTTPException(status_code=404, detail=str(error)) from error
        except Exception as error:
            LOG.error("inspection.read.failed", project_id=project_id, error=str(error))
            raise HTTPException(
                status_code=503, detail=f"Cannot read measurements: {error}"
            ) from error

    routes.add_api_route("/jobs/{job_id}", read_job, methods=["GET"], response_model=InspectionRead)

    @routes.get("/latest", response_model=InspectionRead)
    def latest(project_id: str, request: Request, session: SessionDep) -> InspectionRead:
        return read_job(project_id, None, request, session)

    @routes.post("/jobs/{job_id}/cancel", response_model=InspectionRead)
    def cancel(
        project_id: str, job_id: str, request: Request, session: SessionDep
    ) -> InspectionRead:
        _project(session, project_id)
        try:
            return request.app.state.inspection.cancel(
                session, project_id, job_id, operation=operation
            )
        except FileNotFoundError as error:
            LOG.warning("inspection.cancel.not_found", project_id=project_id, error=str(error))
            raise HTTPException(status_code=404, detail=str(error)) from error
        except Exception as error:
            LOG.error("inspection.cancel.failed", project_id=project_id, error=str(error))
            raise HTTPException(
                status_code=503, detail=f"Cannot cancel measurements: {error}"
            ) from error

    return routes


router = APIRouter()
router.include_router(_routes("decode"))
router.include_router(_routes("rhythm"))
router.include_router(_routes("scenes"))
