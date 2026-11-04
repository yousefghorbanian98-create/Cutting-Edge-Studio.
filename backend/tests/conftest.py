"""Shared pytest fixtures. Everything is sandboxed in tmp dirs."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# Must happen before ``app.main`` is imported: the module-level app factory would
# otherwise create directories inside the real user profile.
os.environ.setdefault("CUTTING_EDGE_DATA_DIR", tempfile.mkdtemp(prefix="ce-guard-"))

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        home_dir=tmp_path / "install",
        log_to_file=False,
        log_level="WARNING",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
