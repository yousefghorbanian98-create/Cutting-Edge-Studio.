"""Browser-to-sidecar imports using Starlette's spooled multipart uploads."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, status

from app.api.assets import import_asset
from app.deps import SessionDep, SettingsDep
from app.logging import get_logger
from app.models import MediaAsset, Project
from app.schemas_media import AssetCreate, AssetRead, Role

router = APIRouter(tags=["media"])
LOG = get_logger(__name__)
MAX_IMPORT_BYTES = 20 * 1024**3
COPY_BUFFER_BYTES = 1024**2
MEDIA_SUFFIXES = {
    ".mp4",
    ".mov",
    ".m4v",
    ".mkv",
    ".webm",
    ".avi",
    ".wav",
    ".mp3",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
}


@router.post(
    "/projects/{project_id}/uploads",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import a browser-selected file into local project storage",
)
def upload_asset(
    project_id: str,
    file: UploadFile,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    role: Annotated[Role, Form()] = "source",
) -> AssetRead:
    """Copy a spooled upload, probe it and persist a real asset; never trust client paths."""
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in MEDIA_SUFFIXES:
        raise HTTPException(status_code=422, detail="Unsupported media extension")
    if not file.size or file.size > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="File must be nonempty and at most 20 GB")

    if shutil.disk_usage(settings.data_dir).free < file.size + COPY_BUFFER_BYTES:
        raise HTTPException(status_code=507, detail="Not enough disk space for local import")

    role_directories = {
        "reference": "references",
        "music": "music",
        "broll": "b-roll",
        "voiceover": "voice-overs",
    }
    directory = (
        settings.data_dir / role_directories[role] / project_id
        if role in role_directories
        else settings.projects_dir / project_id / "imports"
    )
    target = directory / f"{uuid4().hex}{suffix}"
    imported = False
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            shutil.copyfileobj(file.file, output, length=COPY_BUFFER_BYTES)
        asset = import_asset(
            project_id, AssetCreate(path=str(target), role=role), request, session, settings
        )
        row = session.get(MediaAsset, asset.id)
        assert row is not None
        cached = json.loads(row.probe_json)
        cached["ce_import"] = {
            "name": Path((file.filename or target.name).replace("\\", "/")).name,
            "size_bytes": file.size,
        }
        row.probe_json = json.dumps(cached, ensure_ascii=False)
        asset = asset.model_copy(
            update={"name": cached["ce_import"]["name"], "size_bytes": file.size}
        )
        # Commit before declaring success, so failed DB writes also remove the copied file.
        session.commit()
        imported = True
        LOG.info("media.upload.imported", project_id=project_id, asset_id=asset.id, size=file.size)
    except HTTPException as error:
        LOG.warning("media.upload.rejected", project_id=project_id, error=str(error.detail))
        raise
    except Exception as error:
        LOG.error("media.upload.failed", project_id=project_id, error=str(error))
        raise HTTPException(status_code=503, detail=f"Local import failed: {error}") from error
    else:
        return asset
    finally:
        file.file.close()
        if not imported:
            try:
                target.unlink(missing_ok=True)
            except OSError as error:
                LOG.error("media.upload.cleanup_failed", path=str(target), error=str(error))
                raise HTTPException(
                    status_code=503, detail="Import failed; temporary file cleanup also failed"
                ) from error
