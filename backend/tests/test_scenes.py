"""scdet JSON/provenance/job glue fixtures; real native acceptance is separate."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from copy import deepcopy
from pathlib import Path

import pytest
from app.main import create_app
from app.models import Artifact
from app.schemas_inspection import InspectionRead
from app.schemas_media import AssetRead
from app.schemas_scenes import CutCandidate, SceneFile
from app.services.media.ffmpeg import FFmpegBinaries
from app.services.media.probe import parse_probe
from app.services.media.runner import CommandCancelledError, CommandResult
from app.services.media.scenes import FFmpegSceneInspector, measured_candidates, scene_command
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.fixtures import FFPROBE_VIDEO
from tests.test_assets_api import FakeProber
from tests.test_inspection import finished, inputs


def observations():
    return {
        "frames": [
            {"pts_time": "5.0", "tags": {"lavfi.scd.score": "0"}},
            {"pts_time": "5.5", "tags": {"lavfi.scd.score": "0"}},
            {"pts_time": "6.0", "tags": {"lavfi.scd.score": "20", "lavfi.scd.time": "6.0"}},
        ]
    }


def test_native_json_normalizes_pts_not_a_video_timeline_or_semantic_label():
    result = measured_candidates(json.dumps(observations()), 2)
    assert result.frames_analyzed == 3
    assert result.first_frame_pts_seconds == 5
    assert result.time_origin == "first-decoded-video-frame"
    assert result.candidates == [CutCandidate(frame_index=2, time_seconds=1, score_percent=20)]


@pytest.mark.parametrize(
    "fault",
    [
        "empty",
        "missing_pts",
        "nan",
        "bad_score",
        "missing_score",
        "missing_time",
        "wrong_time",
        "duplicate",
        "duration",
    ],
)
def test_malformed_or_incomplete_native_observations_never_become_results(fault):
    body = observations()
    frame = body["frames"][-1]
    if fault == "empty":
        body["frames"] = []
    elif fault == "missing_pts":
        del frame["pts_time"]
    elif fault == "nan":
        frame["tags"]["lavfi.scd.score"] = "nan"
    elif fault == "bad_score":
        frame["tags"]["lavfi.scd.score"] = "101"
    elif fault == "missing_score":
        del frame["tags"]["lavfi.scd.score"]
    elif fault == "missing_time":
        del frame["tags"]["lavfi.scd.time"]
    elif fault == "wrong_time":
        frame["tags"]["lavfi.scd.time"] = "6.1"
    elif fault == "duplicate":
        frame["pts_time"] = "5.5"
    with pytest.raises((ValueError, ValidationError)):
        measured_candidates(json.dumps(body), 0.5 if fault == "duration" else 2)


def test_rounding_at_native_threshold_is_not_reinterpreted_as_our_own_detector():
    body = {"frames": [{"pts_time": "0", "tags": {"lavfi.scd.score": "10.000"}}]}
    assert measured_candidates(json.dumps(body), 1).candidates == []


class FixtureSceneInspector:
    """Explicit injected unit data; production always invokes native tooling."""

    def inspect(self, asset, cancel, progress):
        if cancel.is_set():
            raise CommandCancelledError("Fixture cancelled")
        progress(10)
        path = Path(asset.path)
        stat = path.stat()
        return SceneFile(
            asset_id=asset.id,
            role=asset.role,
            name=asset.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            size_bytes=stat.st_size,
            mtime_ns=str(stat.st_mtime_ns),
            duration=asset.duration,
            has_audio=True,
            has_video=True,
            status="candidates",
            estimate=measured_candidates(json.dumps(observations()), 2),
        )


@pytest.fixture
def scene_client(settings):
    settings.shot_candidates_enabled = True
    binaries = settings.binaries_dir / "ffmpeg" / "bin"
    binaries.mkdir(parents=True)
    for name in ("ffmpeg", "ffprobe"):
        (binaries / name).touch()
    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as client:
        client.app.state.inspection.scene_inspector = FixtureSceneInspector()
        yield client


def scene_inputs(client):
    project, assets, url, body = inputs(client)
    return project, assets, url.replace("/inspection", "/scenes"), body


def test_scene_job_scoped_artifact_survives_restart_without_other_operation_leak(scene_client):
    client = scene_client
    project, _, url, body = scene_inputs(client)
    response = client.post(f"{url}/jobs", json=body)
    assert response.status_code == 202
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "done"
    assert result["operation"] == "scenes"
    assert result["report"]["scope"] == "shot-candidates-only"
    for operation in ("inspection", "rhythm"):
        assert (
            client.get(f"/api/v1/projects/{project}/{operation}/jobs/{result['id']}").status_code
            == 404
        )
    with client.app.state.session_factory() as session:
        assert session.get(Artifact, result["id"]).kind == "shot-candidates"
    with TestClient(create_app(client.app.state.settings)) as restarted:
        assert restarted.get(f"{url}/latest").json() == result


def test_disabled_scenes_profile_returns_reason_not_fake_model_readiness(scene_client):
    client = scene_client
    client.app.state.settings.shot_candidates_enabled = False
    _, _, url, body = scene_inputs(client)
    caps = client.get(f"{url}/capabilities").json()
    assert not caps["inspection"]["available"]
    assert "disabled" in caps["inspection"]["reason"]
    assert not caps["model_analysis"]["available"]
    assert client.post(f"{url}/jobs", json=body).status_code == 503


def test_cancelled_scene_job_blocks_other_operation_and_has_no_success(scene_client):
    client = scene_client
    entered = threading.Event()

    class HeldInspector:
        def inspect(self, _asset, cancel, progress):
            entered.set()
            progress(10)
            cancel.wait(3)
            raise CommandCancelledError("Fixture cancelled")

    client.app.state.inspection.scene_inspector = HeldInspector()
    project, _, url, body = scene_inputs(client)
    job = client.post(f"{url}/jobs", json=body).json()
    assert entered.wait(2)
    assert client.post(f"/api/v1/projects/{project}/inspection/jobs", json=body).status_code == 409
    assert client.post(f"{url}/jobs/{job['id']}/cancel").status_code == 200
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "cancelled"
    assert result["report"] is None
    assert result["percent"] < 100


def probe_payload(fault):
    payload = deepcopy(FFPROBE_VIDEO)
    payload["streams"][0]["index"] = 1  # audio may be before the first video stream
    if fault == "no-video":
        payload["streams"] = payload["streams"][1:]
    if fault == "long":
        payload["format"]["duration"] = "601"
    if fault == "wrong-index":
        payload["streams"][0]["index"] = "1,scdet=threshold=0"

    return payload


@pytest.mark.parametrize(
    "fault",
    [None, "no-video", "timeout", "mutated", "link", "long", "wrong-index", "decode-stderr"],
)
def test_processor_uses_fixed_hardlink_and_real_json_boundary(
    scene_client, monkeypatch, fault, caplog
):
    client = scene_client
    _, assets, _, _ = scene_inputs(client)
    settings = client.app.state.settings
    # The path contains filter metacharacters/Unicode: none may enter the graph.
    original = Path(assets[0]["path"])
    odd = original.with_name("مرجع ' [] : , =.mp4")
    original.rename(odd)
    asset = AssetRead.model_validate({**assets[0], "path": str(odd)})
    before_bytes = odd.read_bytes()
    calls = []
    payload = probe_payload(fault)

    def command(args, **kwargs: object):
        calls.append((args, kwargs))
        if "-show_streams" in args:
            assert args[args.index("-protocol_whitelist") + 1] == "file"
            return CommandResult(0, json.dumps(payload), "")
        assert "مرجع" not in " ".join(args)
        assert "filename=input:stream_index=1:dec_threads=1" in " ".join(args)
        assert (kwargs["cwd"] / "input").read_bytes() == before_bytes
        if fault == "timeout":
            raise TimeoutError("Fixture native deadline")
        if fault == "mutated":
            odd.write_bytes(b"changed original input")
        return CommandResult(
            0,
            json.dumps(observations()),
            "Fixture decoder error" if fault == "decode-stderr" else "",
        )

    if fault == "link":

        def no_link(*_: object):
            raise OSError("Fixture unsupported hardlink volume")

        monkeypatch.setattr("app.services.media.scenes.os.link", no_link)
    monkeypatch.setattr("app.services.media.scenes.run_command", command)
    inspector = FFmpegSceneInspector(settings)
    if fault not in (None, "no-video"):
        with pytest.raises((ValueError, RuntimeError, TimeoutError)):
            inspector.inspect(asset, threading.Event(), lambda _: None)
    else:
        result = inspector.inspect(asset, threading.Event(), lambda _: None)
        assert result.sha256 == hashlib.sha256(before_bytes).hexdigest()
        assert result.status == ("no-video" if fault else "candidates")
        assert len(calls) == (1 if fault else 2)
    assert not list(settings.cache_dir.glob("managed-scenes-*"))
    if fault != "mutated":
        assert odd.read_bytes() == before_bytes
    if fault == "link":
        assert "scenes.stage.failed" in caplog.text
    if fault == "decode-stderr":
        assert "scenes.native.errors" in caplog.text


def test_scene_command_requires_an_integer_index_only():
    binaries = FFmpegBinaries(Path("ffmpeg"), Path("ffprobe"))
    assert "format_opts=protocol_whitelist=file" in " ".join(scene_command(binaries, 0))
    with pytest.raises(ValueError, match="stream index"):
        scene_command(binaries, video_index=True)


def test_scene_failure_is_logged_and_visible_without_a_partial_success(scene_client, caplog):
    client = scene_client

    class BrokenInspector:
        def inspect(self, _asset, _cancel, _progress):
            raise ValueError("Fixture unsupported video input; import a supported local clip")

    client.app.state.inspection.scene_inspector = BrokenInspector()
    _, _, url, body = scene_inputs(client)
    client.post(f"{url}/jobs", json=body)
    finished(client)
    result = client.get(f"{url}/latest").json()
    assert result["state"] == "failed"
    assert result["report"] is None
    assert result["percent"] < 100
    assert "supported local clip" in result["error"]
    assert "inspection.failed" in caplog.text


def test_scene_report_marks_replaced_source_bytes_stale_after_save(scene_client):
    client = scene_client
    _, assets, url, body = scene_inputs(client)
    client.post(f"{url}/jobs", json=body)
    finished(client)
    assert client.get(f"{url}/latest").status_code == 200
    Path(assets[0]["path"]).write_bytes(b"owned fixture changed on disk")
    response = client.get(f"{url}/latest")
    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["report"] is not None


def test_scene_orphan_recovers_as_interrupted_not_success(scene_client):
    client = scene_client
    project, _, url, body = scene_inputs(client)
    record = InspectionRead(
        id="scene-orphan",
        project_id=project,
        operation="scenes",
        **body,
        state="running",
        percent=10,
    )
    with client.app.state.session_factory() as session:
        session.add(
            Artifact(
                id=record.id,
                project_id=project,
                kind="shot-candidates",
                payload_json=record.model_dump_json(),
            )
        )
        session.commit()
    restored = client.get(f"{url}/latest").json()
    assert restored["state"] == "interrupted"
    assert restored["percent"] == 10
    assert restored["report"] is None
    assert "restarted" in restored["error"]
    assert client.get(f"{url}/latest").json() == restored


def test_source_replaced_between_hardlink_and_baseline_is_not_misidentified(
    scene_client, monkeypatch
):
    client = scene_client
    _, assets, _, _ = scene_inputs(client)
    asset = AssetRead.model_validate(assets[0])
    original_link = os.link

    def replaced_during_stage(source, target):
        original_link(source, target)
        Path(source).unlink()
        Path(source).write_bytes(b"replacement between hardlink and baseline")

    monkeypatch.setattr("app.services.media.scenes.os.link", replaced_during_stage)
    with pytest.raises(ValueError, match="Input changed"):
        FFmpegSceneInspector(client.app.state.settings).inspect(
            asset, threading.Event(), lambda _: None
        )
    assert not list(client.app.state.settings.cache_dir.glob("managed-scenes-*"))
