"""Versioned SQLite workspaces: durable save, validation and stale-writer rejection."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest
from app.main import create_app
from app.services.media.probe import parse_probe
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Update
from tests.fixtures import FFPROBE_VIDEO
from tests.test_assets_api import FakeProber


@pytest.fixture
def workspace_client(settings):
    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as client:
        yield client


def make_workspace(client):
    project = client.post("/api/v1/projects", json={"name": "بازی اول"}).json()
    asset = client.post(
        f"/api/v1/projects/{project['id']}/uploads", files={"file": ("گل زیبا.mp4", b"media")}
    ).json()
    url = f"/api/v1/projects/{project['id']}/workspace"
    revision = client.get(url).json()["revision"]
    snapshot = {
        "version": 1,
        "timeline": {
            "tracks": [
                {"id": "v1", "name": "Video 1", "kind": "video", "locked": False, "muted": True}
            ],
            "clips": [
                {
                    "id": "clip-1",
                    "mediaId": asset["path"],
                    "name": asset["name"],
                    "trackId": "v1",
                    "start": 2,
                    "duration": 5,
                    "inPoint": 1,
                    "kind": "video",
                }
            ],
            "bookmarks": [{"id": "mark-1", "time": 3, "label": "گل", "color": "#ffcc00"}],
            "duration": 120,
            "playhead": 3.5,
            "pxPerSecond": 80,
            "snapEnabled": False,
        },
        "mediaOrder": [asset["id"]],
        "selectedAssetId": asset["id"],
        "referenceAssetId": None,
        "wizardStep": 2,
        "post": {
            "enabled": {
                "replay": True,
                "comparison": False,
                "captions": True,
                "broll": False,
                "loudness": True,
                "thumbnail": True,
                "templates": False,
            },
            "presetId": "youtube",
            "layout": "stacked",
            "captionFormat": "srt",
            "quality": "preview",
        },
        "appearance": {"language": "fa", "theme": "glass"},
    }
    return (
        project,
        asset,
        url,
        {"base_revision": revision, "name": "ذخیرهٔ مسابقه", "snapshot": snapshot},
    )


def test_workspace_roundtrip_and_renaming(workspace_client):
    project, asset, url, payload = make_workspace(workspace_client)
    saved = workspace_client.put(url, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] != payload["base_revision"]
    assert saved.json()["snapshot"] == payload["snapshot"]
    assert workspace_client.get(url).json() == saved.json()
    assert (
        workspace_client.get(f"/api/v1/projects/{project['id']}").json()["name"] == payload["name"]
    )
    listed = workspace_client.get(f"/api/v1/projects/{project['id']}/assets").json()[0]
    assert listed["name"] == "گل زیبا.mp4"
    assert listed["size_bytes"] == 5
    assert listed["available"] is True
    assert asset["name"] != asset["path"].split("/")[-1]


def test_workspace_and_names_survive_backend_restart(settings):
    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as first:
        project, _, url, payload = make_workspace(first)
        saved = first.put(url, json=payload).json()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(url).json() == saved
        asset = restarted.get(f"/api/v1/projects/{project['id']}/assets").json()[0]
        assert (asset["name"], asset["size_bytes"], asset["available"]) == ("گل زیبا.mp4", 5, True)


def test_stale_tab_cannot_overwrite_newer_state(workspace_client):
    _, _, url, payload = make_workspace(workspace_client)
    first = workspace_client.put(url, json=payload).json()
    stale = copy.deepcopy(payload)
    stale["snapshot"]["timeline"]["clips"] = []
    stale["name"] = "Stale writer"
    response = workspace_client.put(url, json=stale)
    assert response.status_code == 409
    assert workspace_client.get(url).json() == first


@pytest.mark.parametrize("state", ["broken-json", '{"version":999}', '{"step":3}'])
def test_corrupt_or_unknown_state_is_not_silently_reset(workspace_client, state):
    project, _, url, _ = make_workspace(workspace_client)
    workspace_client.patch(f"/api/v1/projects/{project['id']}", json={"state_json": state})
    response = workspace_client.get(url)
    assert response.status_code == 409
    assert "preserved" in response.json()["detail"]
    assert workspace_client.get(f"/api/v1/projects/{project['id']}").json()["state_json"] == state


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(version=2),
        lambda s: s.update(future=True),
        lambda s: s["timeline"]["clips"][0].update(trackId="missing"),
        lambda s: s["timeline"]["clips"].append(copy.deepcopy(s["timeline"]["clips"][0])),
        lambda s: s["timeline"]["tracks"].append(copy.deepcopy(s["timeline"]["tracks"][0])),
        lambda s: s["timeline"]["bookmarks"].append(copy.deepcopy(s["timeline"]["bookmarks"][0])),
        lambda s: s["timeline"]["clips"][0].update(start=-1),
        lambda s: s["timeline"]["clips"][0].update(duration=999),
        lambda s: s["timeline"].update(pxPerSecond=0),
        lambda s: s["post"].update(presetId="unknown"),
        lambda s: s["post"].update(enabled={}),
        lambda s: s["timeline"]["clips"][0].update(start=True),
        lambda s: s["timeline"].update(playhead=999),
        lambda s: s["timeline"]["bookmarks"][0].update(time=999),
    ],
    ids=[
        "version",
        "unknown_field",
        "unknown_track",
        "duplicate_clip",
        "duplicate_track",
        "duplicate_bookmark",
        "negative_start",
        "out_of_bounds",
        "bad_zoom",
        "bad_post",
        "partial_features",
        "boolean_time",
        "bad_playhead",
        "bad_bookmark",
    ],
)
def test_invalid_snapshot_does_not_change_project(workspace_client, mutate):
    _, _, url, payload = make_workspace(workspace_client)
    mutate(payload["snapshot"])
    response = workspace_client.put(url, json=payload)
    assert response.status_code == 422, response.text
    assert workspace_client.get(url).json()["snapshot"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "media_order",
        "selected",
        "reference",
        "wrong_role",
        "path",
        "kind",
        "source_duration",
        "duplicate_order",
    ],
)
def test_foreign_or_invalid_asset_references_rejected(workspace_client, mutation):
    _, asset, url, payload = make_workspace(workspace_client)
    snapshot = payload["snapshot"]
    if mutation == "media_order":
        snapshot["mediaOrder"] = ["foreign"]
    elif mutation == "selected":
        snapshot["selectedAssetId"] = "foreign"
    elif mutation == "reference":
        snapshot["referenceAssetId"] = "foreign"
    elif mutation == "wrong_role":
        snapshot["referenceAssetId"] = asset["id"]
    elif mutation == "path":
        snapshot["timeline"]["clips"][0]["mediaId"] = "/another/project.mp4"
    elif mutation == "kind":
        snapshot["timeline"]["tracks"][0]["kind"] = "audio"
        snapshot["timeline"]["clips"][0]["kind"] = "audio"
    elif mutation == "source_duration":
        snapshot["timeline"]["clips"][0]["duration"] = 20
    elif mutation == "duplicate_order":
        snapshot["mediaOrder"] *= 2
    response = workspace_client.put(url, json=payload)
    assert response.status_code == 422, response.text
    assert workspace_client.get(url).json()["snapshot"] is None


def test_unknown_project(workspace_client):
    _, _, _, payload = make_workspace(workspace_client)
    assert workspace_client.get("/api/v1/projects/nope/workspace").status_code == 404
    assert workspace_client.put("/api/v1/projects/nope/workspace", json=payload).status_code == 404


def test_atomic_update_race_does_not_report_success(workspace_client, monkeypatch):
    _, _, url, payload = make_workspace(workspace_client)
    original = Session.execute

    def execute(session, statement, *args: object, **kwargs: object):
        if isinstance(statement, Update):
            return SimpleNamespace(rowcount=0)
        return original(session, statement, *args, **kwargs)

    monkeypatch.setattr(Session, "execute", execute)
    assert workspace_client.put(url, json=payload).status_code == 409
    assert workspace_client.get(url).json()["snapshot"] is None


def test_filename_fallback_and_missing_media_are_visible(workspace_client, tmp_path):
    project, asset, _, _ = make_workspace(workspace_client)
    from pathlib import Path

    Path(asset["path"]).unlink()
    listing = workspace_client.get(f"/api/v1/projects/{project['id']}/assets").json()
    assert listing[0]["available"] is False
    assert listing[0]["name"] == "گل زیبا.mp4"
    assert listing[0]["size_bytes"] == 5
    legacy = tmp_path / "original.mp4"
    legacy.write_bytes(b"legacy")
    added = workspace_client.post(
        f"/api/v1/projects/{project['id']}/assets", json={"path": str(legacy)}
    ).json()
    assert (added["name"], added["size_bytes"]) == ("original.mp4", 6)


def test_failed_commit_is_logged_and_never_reported_as_saved(workspace_client, monkeypatch, caplog):
    from sqlalchemy.exc import SQLAlchemyError

    _, _, url, payload = make_workspace(workspace_client)

    def failed_commit(_session):
        raise SQLAlchemyError("disk full")

    monkeypatch.setattr(Session, "commit", failed_commit)
    response = workspace_client.put(url, json=payload)
    assert response.status_code == 503
    assert "unsaved edits" in response.json()["detail"]
    assert "workspace.save.failed" in caplog.text
    monkeypatch.undo()
    assert workspace_client.get(url).json()["snapshot"] is None


def test_delete_cannot_remove_saved_timeline_sources(workspace_client):
    _, asset, url, payload = make_workspace(workspace_client)
    saved = workspace_client.put(url, json=payload).json()
    response = workspace_client.delete(f"/api/v1/assets/{asset['id']}")
    assert response.status_code == 409
    assert "save timeline edits first" in response.json()["detail"]
    assert workspace_client.get(url).json() == saved
    assert workspace_client.get(f"/api/v1/assets/{asset['id']}/content").status_code == 200


def test_delete_unused_media_preserves_original_saved_document(workspace_client):
    project, asset, url, payload = make_workspace(workspace_client)
    payload["snapshot"]["timeline"]["clips"] = []
    saved = workspace_client.put(url, json=payload).json()
    assert workspace_client.delete(f"/api/v1/assets/{asset['id']}").status_code == 204
    assert workspace_client.get(url).json() == saved
    assert workspace_client.get(f"/api/v1/projects/{project['id']}/assets").json() == []


def test_delete_preserves_assets_when_saved_state_is_unreadable(workspace_client, caplog):
    project, asset, _, _ = make_workspace(workspace_client)
    workspace_client.patch(f"/api/v1/projects/{project['id']}", json={"state_json": "broken"})
    response = workspace_client.delete(f"/api/v1/assets/{asset['id']}")
    assert response.status_code == 409
    assert "media was not deleted" in response.json()["detail"]
    assert "media.delete.invalid_workspace" in caplog.text
    assert len(workspace_client.get(f"/api/v1/projects/{project['id']}/assets").json()) == 1
