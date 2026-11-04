"""Read-only settings endpoint for the UI (no secrets, no paths outside app data)."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import SettingsDep
from app.schemas import SettingsRead

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsRead, summary="Client settings")
def read_settings(settings: SettingsDep) -> SettingsRead:
    """Expose the subset of settings the frontend is allowed to know."""
    language = settings.language if settings.language in {"fa", "en"} else "fa"
    theme = settings.theme if settings.theme in {"pro", "glass", "minimal"} else "pro"
    return SettingsRead(
        version=settings.version,
        language=language,  # type: ignore[arg-type]
        theme=theme,  # type: ignore[arg-type]
        offline=settings.offline,
        data_dir=str(settings.data_dir),
        home_dir=str(settings.home_dir),
    )
