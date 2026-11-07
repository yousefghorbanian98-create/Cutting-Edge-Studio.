"""Security guard tests — token + Host/Origin + random port."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture(autouse=True)
def _clean_token():
    orig = os.environ.get("CES_API_TOKEN")
    yield
    if orig is None:
        os.environ.pop("CES_API_TOKEN", None)
    else:
        os.environ["CES_API_TOKEN"] = orig


def make_client(token: str | None, tmp_path: Path) -> TestClient:
    if token is not None:
        os.environ["CES_API_TOKEN"] = token
    else:
        os.environ.pop("CES_API_TOKEN", None)
        os.environ.pop("CES_GENERATE_TOKEN", None)
    from app.main import create_app

    settings = Settings(data_dir=tmp_path / "data", home_dir=tmp_path / "install", log_to_file=False, log_level="WARNING")
    client = TestClient(create_app(settings))
    return client


def test_401_without_token_when_enforced(tmp_path):
    client = make_client("s3cr3t-token", tmp_path)
    r = client.get("/api/v1/health", headers={"Host": "127.0.0.1:8756"})
    assert r.status_code == 401


def test_200_with_correct_token(tmp_path):
    client = make_client("s3cr3t-token", tmp_path)
    r = client.get("/api/v1/health", headers={"Host": "127.0.0.1:8756", "x-ces-token": "s3cr3t-token"})
    assert r.status_code == 200


def test_403_bad_host(tmp_path):
    client = make_client("s3cr3t-token", tmp_path)
    r = client.get("/api/v1/health", headers={"Host": "evil.com", "x-ces-token": "s3cr3t-token"})
    assert r.status_code == 403


def test_403_bad_origin(tmp_path):
    client = make_client("s3cr3t-token", tmp_path)
    r = client.get("/api/v1/health", headers={"Host": "127.0.0.1:8756", "Origin": "https://evil.com", "x-ces-token": "s3cr3t-token"})
    assert r.status_code == 403


def test_options_bypass(tmp_path):
    client = make_client("s3cr3t-token", tmp_path)
    r = client.options("/api/v1/health", headers={"Host": "127.0.0.1:8756"})
    # OPTIONS is allowed without token (CORS preflight)
    assert r.status_code in (200, 204, 405)  # 405 if not explicitly handled, but not 401/403


def test_no_token_allows_when_not_enforced(tmp_path):
    client = make_client(None, tmp_path)
    r = client.get("/api/v1/health", headers={"Host": "127.0.0.1:8756"})
    assert r.status_code == 200


def test_desktop_listener_random_port(tmp_path):
    # Verify port 0 binds and returns actual port
    from app.__main__ import desktop_listener

    settings = Settings(data_dir=tmp_path / "data", home_dir=tmp_path / "install", host="127.0.0.1", port=0, log_to_file=False, log_level="WARNING")
    listener = desktop_listener(settings)
    try:
        assert listener.getsockname()[1] != 0
    finally:
        listener.close()


def test_receipt_contains_origin(tmp_path):
    # Receipt publish should include correct origin with port
    from app.desktop import publish_receipt, clear_receipt

    settings = Settings(
        data_dir=tmp_path / "data",
        home_dir=tmp_path / "install",
        host="127.0.0.1",
        port=8756,
        desktop_instance_id="123-456",
        desktop_ready_file=tmp_path / "ready.json",
        log_to_file=False,
    )
    settings.ensure_dirs()
    publish_receipt(settings, listener_owned=False)
    assert settings.desktop_ready_file.exists()
    import json

    data = json.loads(settings.desktop_ready_file.read_text())
    assert data["origin"] == "http://127.0.0.1:8756"
    assert data["instance_id"] == "123-456"
    clear_receipt(settings)
