"""Health/readiness endpoint consumed by the Tauri shell and smoke tests."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import SettingsDep
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health(settings: SettingsDep) -> HealthResponse:
    """Report process health without touching the network."""
    return HealthResponse(
        version=settings.version,
        app_name=settings.app_name,
        offline=settings.offline,
        database=str(settings.db_path),
        models_dir=str(settings.models_dir),
    )
