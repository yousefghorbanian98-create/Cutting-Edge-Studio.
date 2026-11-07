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
def media_client(settings: Settings, media_file: Path):
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


def test_browser_upload_persists_bytes_and_real_asset(
    media_client: TestClient, settings: Settings
) -> None:
    project_id = _project(media_client)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files={"file": ("../../source.MP4", b"test-media", "video/mp4")},
        data={"role": "reference"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    stored = Path(body["path"])
    assert stored.parent == settings.data_dir / "references" / project_id
    assert stored.suffix == ".mp4"
    assert stored.read_bytes() == b"test-media"
    assert body["role"] == "reference"
    assert body["video_codec"] == "h264"
    assert body["has_audio"] is True
    assert media_client.get(f"/api/v1/projects/{project_id}/assets").json()[0]["id"] == body["id"]
    content = media_client.get(f"/api/v1/assets/{body['id']}/content")
    assert content.content == b"test-media"
    assert content.headers["cache-control"] == "no-store"
    partial = media_client.get(
        f"/api/v1/assets/{body['id']}/content", headers={"Range": "bytes=2-5"}
    )
    assert partial.status_code == 206
    assert partial.content == b"st-m"


@pytest.mark.parametrize(
    ("filename", "data", "expected"), [("file.exe", b"abc", 422), ("a.mp4", b"", 413)]
)
def test_upload_rejects_invalid_input(media_client, settings, filename, data, expected) -> None:
    project_id = _project(media_client)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/uploads", files={"file": (filename, data)}
    )
    assert response.status_code == expected
    assert list(settings.projects_dir.rglob("*.mp4")) == []
    assert media_client.get(f"/api/v1/projects/{project_id}/assets").json() == []


def test_upload_unknown_project_and_invalid_role(media_client) -> None:
    response = media_client.post("/api/v1/projects/nope/uploads", files={"file": ("a.mp4", b"x")})
    assert response.status_code == 404
    project_id = _project(media_client)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files={"file": ("a.mp4", b"x")},
        data={"role": "unknown"},
    )
    assert response.status_code == 422


def test_upload_limits_size(media_client, monkeypatch) -> None:
    from app.api import uploads

    project_id = _project(media_client)
    monkeypatch.setattr(uploads, "MAX_IMPORT_BYTES", 3)
    response = media_client.post(
        f"/api/v1/projects/{project_id}/uploads", files={"file": ("a.mp4", b"four")}
    )
    assert response.status_code == 413


def test_upload_checks_free_space(media_client, monkeypatch) -> None:
    from types import SimpleNamespace

    from app.api import uploads

    project_id = _project(media_client)
    monkeypatch.setattr(uploads.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    response = media_client.post(
        f"/api/v1/projects/{project_id}/uploads", files={"file": ("a.mp4", b"x")}
    )
    assert response.status_code == 507


def test_failed_upload_cleans_copy_and_does_not_create_asset(settings) -> None:
    app = create_app(settings, prober=ExplodingProber())
    with TestClient(app) as client:
        project_id = _project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/uploads", files={"file": ("a.mp4", b"x")}
        )
        assert response.status_code == 503
        assert "ffprobe unavailable" in response.json()["detail"]
        assert list(settings.projects_dir.rglob("*.mp4")) == []
        assert client.get(f"/api/v1/projects/{project_id}/assets").json() == []


def test_content_unknown_asset_or_missing_file(media_client, media_file) -> None:
    assert media_client.get("/api/v1/assets/nope/content").status_code == 404
    project_id = _project(media_client)
    body = media_client.post(
        f"/api/v1/projects/{project_id}/assets", json={"path": str(media_file)}
    ).json()
    media_file.unlink()
    assert media_client.get(f"/api/v1/assets/{body['id']}/content").status_code == 404
