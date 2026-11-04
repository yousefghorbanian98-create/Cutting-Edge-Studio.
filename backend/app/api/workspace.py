"""Atomic versioned workspace save/load with optimistic concurrency protection."""

from __future__ import annotations

import json
from hashlib import sha256

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.deps import SessionDep
from app.logging import get_logger
from app.models import MediaAsset, Project
from app.schemas_workspace import WorkspaceRead, WorkspaceSave, WorkspaceSnapshot

router = APIRouter(prefix="/projects", tags=["workspace"])
LOG = get_logger(__name__)


def _project(session: SessionDep, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _revision(project: Project) -> str:
    return sha256(json.dumps([project.name, project.state_json]).encode()).hexdigest()


@router.get("/{project_id}/workspace", response_model=WorkspaceRead)
def read_workspace(project_id: str, session: SessionDep) -> WorkspaceRead:
    """Legacy empty projects are supported; corrupt/unknown snapshots are never discarded."""
    project = _project(session, project_id)
    snapshot = None
    if project.state_json.strip() != "{}":
        try:
            snapshot = WorkspaceSnapshot.model_validate_json(project.state_json)
        except ValidationError as error:
            LOG.error("workspace.invalid_saved_state", project_id=project_id, error=str(error))
            raise HTTPException(
                status_code=409,
                detail="Saved workspace is invalid or unsupported; original data preserved",
            ) from error
    return WorkspaceRead(name=project.name, revision=_revision(project), snapshot=snapshot)


def _validate_assets(snapshot: WorkspaceSnapshot, project_id: str, session: SessionDep) -> None:
    assets = list(session.scalars(select(MediaAsset).where(MediaAsset.project_id == project_id)))
    by_id = {asset.id: asset for asset in assets}
    by_path = {asset.path: asset for asset in assets}
    if len(set(snapshot.mediaOrder)) != len(snapshot.mediaOrder):
        raise HTTPException(status_code=422, detail="Duplicate media IDs")
    ids = [*snapshot.mediaOrder, snapshot.selectedAssetId, snapshot.referenceAssetId]
    if any(asset_id is not None and asset_id not in by_id for asset_id in ids):
        raise HTTPException(
            status_code=422, detail="Workspace references media outside this project"
        )
    if snapshot.referenceAssetId and by_id[snapshot.referenceAssetId].role != "reference":
        raise HTTPException(status_code=422, detail="Selected reference is not a reference asset")
    for clip in snapshot.timeline.clips:
        asset = by_path.get(clip.mediaId)
        if asset is None or clip.kind != asset.kind:
            raise HTTPException(
                status_code=422, detail="Timeline media is missing from this project"
            )
        if clip.inPoint + clip.duration > asset.duration + 0.05:
            raise HTTPException(
                status_code=422, detail="Timeline clip extends past source duration"
            )


@router.put("/{project_id}/workspace", response_model=WorkspaceRead)
def save_workspace(project_id: str, payload: WorkspaceSave, session: SessionDep) -> WorkspaceRead:
    """Compare-and-swap prevents a stale tab from overwriting another tab's saved edit."""
    try:
        project = _project(session, project_id)
        if payload.base_revision != _revision(project):
            raise HTTPException(
                status_code=409, detail="Workspace changed elsewhere; reopen before saving"
            )
        _validate_assets(payload.snapshot, project_id, session)
        serialized = payload.snapshot.model_dump_json()
        result = session.execute(
            update(Project)
            .where(
                Project.id == project_id,
                Project.state_json == project.state_json,
                Project.name == project.name,
            )
            .values(name=payload.name, state_json=serialized)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise HTTPException(
                status_code=409, detail="Workspace changed during save; reopen before saving"
            )
        session.flush()
        session.refresh(project)
        response = WorkspaceRead(
            name=project.name, revision=_revision(project), snapshot=payload.snapshot
        )
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        LOG.error("workspace.save.failed", project_id=project_id, error=str(error))
        raise HTTPException(
            status_code=503,
            detail="Local project save failed; unsaved edits are still in this window",
        ) from error
    else:
        LOG.info(
            "workspace.saved", project_id=project_id, clips=len(payload.snapshot.timeline.clips)
        )
        return response
