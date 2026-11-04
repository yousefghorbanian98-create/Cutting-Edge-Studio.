"""Audio job glue tests: injected measurements are fixtures, not real librosa acceptance."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest
from app.main import create_app
from app.models import Artifact
from app.schemas_rhythm import RhythmEstimate, RhythmFile
from app.services.media.probe import parse_probe
from app.services.media.runner import CommandCancelledError
from fastapi.testclient import TestClient
from tests.fixtures import FFPROBE_VIDEO
from tests.test_assets_api import FakeProber
from tests.test_inspection import finished, inputs


def estimate(**changes: object):
    """Explicit two-second synthetic JSON boundary fixture."""
    return RhythmEstimate.model_validate(
        {
            "sha256": "a" * 64,
            "samples_analyzed": 44100,
            "duration_seconds": 2,
            "tempo_bpm": 120,
            "beat_times_seconds": [0.5, 1, 1.5],
            "library_version": "0.11.0",
            "method": "librosa.beat.beat_track",
            "scope": "audio-rhythm-only",
            **changes,
        }
    )


class FixtureRhythmInspector:
    """Supply one missing-audio reference and a synthetic source estimate."""

    def inspect(self, asset, cancel, progress):
        if cancel.is_set():
            raise CommandCancelledError("Fixture cancelled")
        progress(50)
        path = Path(asset.path)
        stat = path.stat()
        audio = asset.role != "reference"
        return RhythmFile(
            asset_id=asset.id,
            role=asset.role,
            name=asset.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            size_bytes=stat.st_size,
            mtime_ns=str(stat.st_mtime_ns),
            duration=asset.duration,
            has_audio=audio,
            status="estimated" if audio else "no-audio",
            estimate=estimate() if audio else None,
        )


class HoldingRhythmInspector(FixtureRhythmInspector):
    """Hold an audio phase until cancellation; no actual inference."""

    def __init__(self) -> None:
        self.entered = threading.Event()

    def inspect(self, asset, cancel, progress):
        self.entered.set()
        progress(50)
        if cancel.wait(5):
            raise CommandCancelledError("Fixture cancelled")
        return super().inspect(asset, cancel, progress)


@pytest.fixture
def rhythm_client(settings, monkeypatch):
    settings.audio_rhythm_enabled = True
    monkeypatch.setattr("app.services.audio.processor.version", lambda _: "0.11.0")
    binaries = settings.binaries_dir / "ffmpeg" / "bin"
    binaries.mkdir(parents=True)
    for name in ("ffmpeg", "ffprobe"):
        (binaries / name).touch()
    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as client:
        client.app.state.inspection.rhythm_inspector = FixtureRhythmInspector()
        yield client


def audio_inputs(client):
    project, assets, url, body = inputs(client)
    return project, assets, url.replace("/inspection", "/rhythm"), body


def test_rhythm_artifact_is_durable_and_operation_scoped(rhythm_client):
    client = rhythm_client
    project, assets, url, body = audio_inputs(client)
    response = client.post(f"{url}/jobs", json=body)
    assert response.status_code == 202
    job = response.json()
    assert job["operation"] == "rhythm"
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "done"
    assert result["report"]["scope"] == "audio-rhythm-only"
    assert [f["status"] for f in result["report"]["files"]] == ["no-audio", "estimated"]
    assert result["report"]["files"][1]["asset_id"] == assets[1]["id"]
    assert client.get(f"/api/v1/projects/{project}/inspection/latest").status_code == 404
    assert client.get(f"/api/v1/projects/{project}/inspection/jobs/{job['id']}").status_code == 404
    assert (
        client.post(f"/api/v1/projects/{project}/inspection/jobs/{job['id']}/cancel").status_code
        == 404
    )
    with client.app.state.session_factory() as session:
        artifact = session.get(Artifact, job["id"])
        assert artifact.kind == "audio-rhythm"
    restored = create_app(client.app.state.settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))
    with TestClient(restored) as restarted:
        saved = restarted.get(f"{url}/latest").json()
        assert saved["report"] == result["report"]
        assert saved["state"] == "done"
        assert not saved["stale"]


def test_rhythm_cancel_and_decode_share_single_worker(rhythm_client):
    client = rhythm_client
    inspector = HoldingRhythmInspector()
    client.app.state.inspection.rhythm_inspector = inspector
    project, _, url, body = audio_inputs(client)
    job = client.post(f"{url}/jobs", json=body).json()
    assert inspector.entered.wait(3)
    conflict = client.post(f"/api/v1/projects/{project}/inspection/jobs", json=body)
    assert conflict.status_code == 409
    assert client.post(f"{url}/jobs/{job['id']}/cancel").status_code == 200
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "cancelled"
    assert result["report"] is None
    assert result["percent"] < 100


def test_rhythm_failure_has_no_success_report(rhythm_client):
    client = rhythm_client

    class FailedInspector:
        def inspect(self, *_: object):
            raise RuntimeError("Fixture worker timed out")

    client.app.state.inspection.rhythm_inspector = FailedInspector()
    _, _, url, body = audio_inputs(client)
    client.post(f"{url}/jobs", json=body)
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "failed"
    assert result["report"] is None
    assert "timed out" in result["error"]


def test_default_disabled_profile_blocks_job_not_decode(rhythm_client):
    client = rhythm_client
    client.app.state.settings.audio_rhythm_enabled = False
    project, _, url, body = audio_inputs(client)
    caps = client.get(f"{url}/capabilities").json()
    assert not caps["inspection"]["available"]
    assert caps["operation"] == "rhythm"
    assert "not enabled" in caps["inspection"]["reason"]
    assert client.post(f"{url}/jobs", json=body).status_code == 503
    assert client.get(f"/api/v1/projects/{project}/inspection/capabilities").json()["inspection"][
        "available"
    ]
    assert client.get(f"{url}/latest").status_code == 404


def test_rhythm_rejects_unregistered_source_and_rechecks_provenance(rhythm_client):
    client = rhythm_client
    _, assets, url, body = audio_inputs(client)
    assert (
        client.post(f"{url}/jobs", json={**body, "source_asset_ids": ["unknown"]}).status_code
        == 422
    )
    client.post(f"{url}/jobs", json=body)
    finished(client)
    Path(assets[1]["path"]).write_bytes(b"changed-input")
    result = client.get(f"{url}/latest").json()
    assert result["stale"]
    assert result["state"] == "done"  # historical artifact is not overwritten with new data


@pytest.mark.parametrize(
    "changes",
    [
        {"tempo_bpm": None},
        {"tempo_bpm": float("nan")},
        {"beat_times_seconds": [1, 0.5]},
        {"beat_times_seconds": [3]},
        {"samples_analyzed": 22050},
        {"duration_seconds": 601},
        {"library_version": "0.12.0"},
    ],
)
def test_invalid_worker_estimates_are_rejected(changes):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        estimate(**changes)


def test_orphaned_rhythm_is_interrupted_and_wrong_operation_is_not_relabelled(rhythm_client):
    client = rhythm_client
    project, _, url, body = audio_inputs(client)
    record = dict(
        id="orphaned-audio",
        project_id=project,
        operation="rhythm",
        **body,
        state="running",
        percent=50,
    )
    with client.app.state.session_factory() as session:
        session.add(
            Artifact(
                id=record["id"],
                project_id=project,
                kind="audio-rhythm",
                payload_json=json.dumps(record),
            )
        )
        session.commit()
    interrupted = client.get(f"{url}/latest").json()
    assert interrupted["state"] == "interrupted"
    assert interrupted["percent"] == 50
    assert interrupted["report"] is None
    with client.app.state.session_factory() as session:
        artifact = session.get(Artifact, record["id"])
        artifact.payload_json = json.dumps({**record, "operation": "decode"})
        session.commit()
    assert client.get(f"{url}/latest").status_code == 503
    with client.app.state.session_factory() as session:
        assert json.loads(session.get(Artifact, record["id"]).payload_json)["operation"] == "decode"
