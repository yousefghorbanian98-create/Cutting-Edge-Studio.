"""R2 — honest analysis orchestration (explicit reference, no synthetic labels)."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import pytest
from app.config import Settings
from app.main import create_app
from app.services.inference.registry import InferenceRegistry, ModelSpec, ModelUnavailableError
from app.services.stylematch.analysis import AnalysisOrchestrator, analysis_unavailable
from fastapi.testclient import TestClient


def _settings(tmp: Path) -> Settings:
    return Settings(data_dir=tmp / "data", home_dir=tmp / "home", log_to_file=False)


def test_analysis_unavailable_blocks_without_models(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    reason = analysis_unavailable(settings)
    assert reason is not None
    assert "no runtime downloads" in reason.lower()
    assert "verified" in reason.lower()
    assert "mediapipe-pose" in reason


def test_analysis_unavailable_passes_when_all_model_dirs_present(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    registry = InferenceRegistry()
    for spec in registry.specs():
        d = settings.models_dir / spec.name
        d.mkdir(parents=True, exist_ok=True)
        (d / "pinned.bin").write_bytes(b"x")
    assert analysis_unavailable(settings, registry) is None


def test_orchestrator_blocks_and_reports_actionable_error_via_api(settings) -> None:
    # Standalone client with fake binaries so analysis path is exercised
    binaries = settings.binaries_dir / "ffmpeg" / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg", "ffprobe"):
        (binaries / name).touch()
    # Reuse the inspection fixture pattern but for analysis
    from app.services.media.probe import parse_probe
    from tests.fixtures import FFPROBE_VIDEO
    from tests.test_assets_api import FakeProber
    from tests.test_inspection import FixtureInspector

    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as client:
        client.app.state.inspection.inspector = FixtureInspector()
        # Create project + assets
        project = client.post("/api/v1/projects", json={"name": "R2"}).json()["id"]
        assets = []
        for role in ("reference", "source"):
            assets.append(
                client.post(
                    f"/api/v1/projects/{project}/uploads",
                    files={"file": (f"{role}.mp4", b"fixture-bytes")},
                    data={"role": role},
                ).json()
            )
        payload = {"reference_asset_id": assets[0]["id"], "source_asset_ids": [assets[1]["id"]]}
        analysis_url = f"/api/v1/projects/{project}/analysis"
        caps = client.get(analysis_url + "/capabilities").json()
        assert caps["operation"] == "analysis"
        assert caps["inspection"]["available"] is False
        assert "no runtime downloads" in caps["model_analysis"]["reason"].lower()
        assert "no runtime downloads" in caps["inspection"]["reason"].lower()

        resp = client.post(analysis_url + "/jobs", json=payload)
        assert resp.status_code == 503
        assert "no runtime downloads" in resp.text.lower()


def test_orchestrator_job_is_durable_and_never_fakes_success(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    registry = InferenceRegistry(
        specs=[ModelSpec("test-model", 10, 1, "fake", loader=lambda: object())]
    )
    orch = AnalysisOrchestrator(settings, registry)
    data_dir = tmp_path / "clip.mp4"
    data_dir.write_bytes(b"fake-video-bytes" * 100)
    from app.schemas_media import AssetRead

    asset = AssetRead(
        id="a" * 32,
        project_id="p",
        path=str(data_dir),
        name="clip.mp4",
        role="reference",
        kind="video",
        duration=5.0,
        fps=30.0,
        width=1080,
        height=1920,
        video_codec="h264",
        audio_codec=None,
        has_audio=False,
        available=True,
        size_bytes=data_dir.stat().st_size,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    with pytest.raises(ModelUnavailableError, match="no runtime downloads"):
        orch.inspect(asset, threading.Event(), lambda _p: None)


def test_analysis_api_explicit_reference_selection_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        settings = _settings(Path(td))
        app = create_app(settings)
        with TestClient(app) as client:
            proj = client.post("/api/v1/projects", json={"name": "R2"}).json()["id"]
            bad = {"reference_asset_id": "b" * 32, "source_asset_ids": ["c" * 32]}
            resp = client.post(f"/api/v1/projects/{proj}/analysis/jobs", json=bad)
            assert resp.status_code == 422
