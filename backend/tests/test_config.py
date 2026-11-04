"""Path resolution and settings behaviour."""

from __future__ import annotations

from pathlib import Path

from app import config
from app.config import Settings, get_settings, reset_settings_cache, user_data_dir


def test_env_override_wins(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CUTTING_EDGE_DATA_DIR", str(tmp_path / "custom"))
    assert user_data_dir() == tmp_path / "custom"


def test_data_dir_platform_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CUTTING_EDGE_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert user_data_dir() == tmp_path / "xdg" / config.APP_NAME


def test_ensure_dirs_creates_tree(settings: Settings) -> None:
    settings.ensure_dirs()
    for path in (settings.data_dir, settings.logs_dir, settings.projects_dir, settings.cache_dir):
        assert path.is_dir()


def test_derived_paths(settings: Settings) -> None:
    assert settings.db_path.name == "cutting-edge.db"
    assert settings.database_url.startswith("sqlite+pysqlite:///")
    assert settings.models_dir == settings.home_dir / "models"
    assert settings.binaries_dir == settings.home_dir / "binaries"


def test_settings_singleton_is_cached() -> None:
    reset_settings_cache()
    first = get_settings()
    assert get_settings() is first
    reset_settings_cache()
    assert get_settings() is not first
