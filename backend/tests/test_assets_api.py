"""Media asset API: import with an injected prober (no FFmpeg needed)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.main import create_app
from app.services.media.probe import MediaInfo, parse_probe
from fastapi.testclient import TestClient
from tests.fixtures import FFPROBE_VIDEO


class FakeProber:
    """Deterministic prober used by the API tests."""

    def __init__(self, info: MediaInfo) -> None:
        self.info = info
        self.calls: list[Path] = []

    def probe(self, path: Path) -> MediaInfo:
        if not path.is_file():
            msg = f"file not found: {path}"
            raise FileNotFoundError(msg)
        self.calls.append(path)
        return self.info


class ExplodingProber:
    """Simulates a missing/broken ffprobe binary."""

    def probe(self, path: Path) -> MediaInfo:
        _ = path
        msg = "ffprobe missing"
        raise RuntimeError(msg)


@pytest.fixture
def media_file(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"fake-mp4")
    return path


@pytest.fixture
def media_client(settings: Settings, media_file: Path):  # noqa: ARG001 - fixture creates the file
    app = create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))
    with TestClient(app) as client:
        yield client


def _project(client: TestClient) -> str:
    response = client.post("/api/v1/projects", json={"name": "Media"})
    assert response.status_code == 201
    return response.json()["id"]


def test_import_probes_and_stores(media_client: TestClient, media_file: Path) -> None:
    project_id = _project(media_client)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/assets",
        json={"path": str(media_file), "role": "source"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "video"
    assert body["duration"] == pytest.approx(12.345)
    assert (body["width"], body["height"]) == (1920, 1080)
    assert body["role"] == "source"

    listing = media_client.get(f"/api/v1/projects/{project_id}/assets").json()
    assert [row["id"] for row in listing] == [body["id"]]


def test_import_is_idempotent_per_path(media_client: TestClient, media_file: Path) -> None:
    project_id = _project(media_client)
    payload = {"path": str(media_file)}
    first = media_client.post(f"/api/v1/projects/{project_id}/assets", json=payload).json()
    second = media_client.post(f"/api/v1/projects/{project_id}/assets", json=payload).json()
    assert first["id"] == second["id"]


def test_import_missing_file_is_404(media_client: TestClient) -> None:
    project_id = _project(media_client)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/assets",
        json={"path": "/nope/missing.mp4"},
    )
    assert response.status_code == 404


def test_unknown_project_is_404(media_client: TestClient, media_file: Path) -> None:
    response = media_client.post("/api/v1/projects/nope/assets", json={"path": str(media_file)})
    assert response.status_code == 404


def test_broken_probe_reports_503_and_logs(settings: Settings, media_file: Path) -> None:
    app = create_app(settings, prober=ExplodingProber())
    with TestClient(app) as client:
        project_id = _project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/assets", json={"path": str(media_file)}
        )
    assert response.status_code == 503
    assert "ffprobe unavailable" in response.json()["detail"]


def test_delete_asset(media_client: TestClient, media_file: Path) -> None:
    project_id = _project(media_client)
    asset = media_client.post(
        f"/api/v1/projects/{project_id}/assets", json={"path": str(media_file)}
    ).json()
    assert media_client.delete(f"/api/v1/assets/{asset['id']}").status_code == 204
    assert media_client.delete(f"/api/v1/assets/{asset['id']}").status_code == 404
    assert media_client.get(f"/api/v1/projects/{project_id}/assets").json() == []


def test_update_asset_role_via_project_delete_cascade(
    media_client: TestClient, media_file: Path
) -> None:
    project_id = _project(media_client)
    media_client.post(
        f"/api/v1/projects/{project_id}/assets", json={"path": str(media_file), "role": "reference"}
    )
    assert media_client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    assert media_client.get(f"/api/v1/projects/{project_id}/assets").status_code == 404


def test_proxy_job_fails_gracefully_without_ffmpeg(
    media_client: TestClient, media_file: Path
) -> None:
    project_id = _project(media_client)
    asset = media_client.post(
        f"/api/v1/projects/{project_id}/assets", json={"path": str(media_file)}
    ).json()
    response = media_client.post(f"/api/v1/assets/{asset['id']}/proxy")
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert media_client.get(f"/api/v1/jobs/{job_id}").status_code == 200
    assert job_id in [job["id"] for job in media_client.get("/api/v1/jobs").json()]
    assert media_client.get("/api/v1/jobs/nope").status_code == 404


def test_encoder_endpoint_degrades_without_ffmpeg(media_client: TestClient) -> None:
    response = media_client.get("/api/v1/media/encoder")
    assert response.status_code == 200
    body = response.json()
    assert body["encoder"] is None
    assert body["hardware"] is False
