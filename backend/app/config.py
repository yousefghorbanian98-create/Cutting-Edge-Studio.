"""Application configuration and offline-first path resolution.

All settings are local. The application never performs network requests at runtime
(see OFFLINE POLICY in the protocol); the only optional downloads are gated behind
explicit user actions in the UI and are not reachable from this module.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "CuttingEdgeV2"
APP_VERSION = "1.0.0"
API_PREFIX = "/api/v1"

#: Loopback origins of the Tauri / Vite dev shells. Nothing else is allowed.
ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "https://tauri.localhost",
)


def user_data_dir() -> Path:
    """Return the per-user data directory (``%APPDATA%`` on Windows)."""
    override = os.environ.get("CUTTING_EDGE_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / APP_NAME


def program_dir() -> Path:
    """Return the install directory that holds bundled models/binaries/templates."""
    override = os.environ.get("CUTTING_EDGE_HOME")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):  # PyInstaller sidecar
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings, overridable through ``CUTTING_EDGE_*`` env variables."""

    model_config = SettingsConfigDict(env_prefix="CUTTING_EDGE_", env_file=None, extra="forbid")

    app_name: str = APP_NAME
    version: str = APP_VERSION
    data_dir: Path = Field(default_factory=user_data_dir)
    home_dir: Path = Field(default_factory=program_dir)
    host: str = "127.0.0.1"
    port: int = Field(default=8756, ge=0, le=65535)
    serve_frontend: bool = False
    desktop_instance_id: str | None = Field(default=None, pattern=r"^[0-9]+-[0-9]+$")
    desktop_ready_file: Path | None = None
    log_level: str = "INFO"
    log_to_file: bool = True
    language: str = "fa"
    theme: str = "pro"
    #: CPU threads given to OSS inference backends (None -> library default).
    inference_threads: int | None = None
    #: Hard requirement: runtime stays offline. Guarded by tests.
    offline: bool = True
    # Experimental local-build gate; optional/native distribution audit is separate.
    audio_rhythm_enabled: bool = False
    shot_candidates_enabled: bool = False

    @property
    def db_path(self) -> Path:
        """SQLite database file."""
        return self.data_dir / "cutting-edge.db"

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL for the local SQLite database."""
        return f"sqlite+pysqlite:///{self.db_path}"

    @property
    def logs_dir(self) -> Path:
        """Directory holding rotating logs."""
        return self.data_dir / "logs"

    @property
    def projects_dir(self) -> Path:
        """Directory holding project files and rendered assets."""
        return self.data_dir / "projects"

    @property
    def cache_dir(self) -> Path:
        """Scratch space for proxies and stage artifacts."""
        return self.data_dir / "cache"

    @property
    def models_dir(self) -> Path:
        """Bundled pre-trained model weights (install directory)."""
        return self.home_dir / "models"

    @property
    def binaries_dir(self) -> Path:
        """Bundled third-party binaries (FFmpeg, Piper, llama-server...)."""
        return self.home_dir / "binaries"

    def ensure_dirs(self) -> None:
        """Create every directory the backend writes to."""
        for path in (self.data_dir, self.logs_dir, self.projects_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def reset_settings_cache() -> None:
    """Drop the cached settings (used by tests and by the settings UI)."""
    get_settings.cache_clear()
