"""Local diagnostics endpoint (support bundle, no telemetry)."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.config import APP_VERSION, Settings, get_settings
from app.logging import get_logger
from app.services.media.ffmpeg import FFmpegNotFoundError, resolve_binaries

router = APIRouter(prefix="/system", tags=["system"])
LOG = get_logger(__name__)


@router.get("/diagnostics", summary="Local environment report (never uploaded)")
def diagnostics() -> dict[str, Any]:
    """Everything support needs, computed from the machine that runs the sidecar."""
    settings: Settings = get_settings()
    data = settings.data_dir
    usage = shutil.disk_usage(data) if data.exists() else shutil.disk_usage(Path(settings.home_dir))
    ffmpeg: dict[str, Any]
    try:
        binaries = resolve_binaries(settings, allow_path_fallback=True)
        ffmpeg = {"found": True, "directory": str(binaries.ffmpeg.parent)}
    except FFmpegNotFoundError as error:
        LOG.warning("system.diagnostics.ffmpeg_missing", error=str(error))
        ffmpeg = {"found": False, "directory": None}

    models_dir = settings.home_dir / "models"
    models = sorted(path.name for path in models_dir.iterdir()) if models_dir.is_dir() else []
    LOG.info("system.diagnostics", version=APP_VERSION, platform=platform.platform())

    return {
        "app": {"name": settings.app_name, "version": APP_VERSION, "offline": settings.offline},
        "python": sys.version.split()[0],
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "paths": {"data_dir": str(data), "home_dir": str(settings.home_dir)},
        "disk": {
            "free_gb": round(usage.free / 1024**3, 1),
            "total_gb": round(usage.total / 1024**3, 1),
        },
        "ffmpeg": ffmpeg,
        "models": models,
        "log_file": str(data / "logs" / "cutting-edge.log") if settings.log_to_file else None,
    }
