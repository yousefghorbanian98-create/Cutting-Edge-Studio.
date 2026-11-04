"""Project CRUD contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

VALID = {
    "name": "Posing 2026",
    "mode": "style-match",
    "sport": "bodybuilding",
    "language": "fa",
    "width": 1080,
    "height": 1920,
    "fps": 30,
}


def _create(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {**VALID, **overrides}
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list(client: TestClient) -> None:
    created = _create(client)
    assert created["name"] == "Posing 2026"
    assert created["mode"] == "style-match"
    listing = client.get("/api/v1/projects").json()
    assert [row["id"] for row in listing] == [created["id"]]


def test_defaults_follow_lock_02(client: TestClient) -> None:
    created = _create(client, name="Defaults")
    assert created["mode"] == "style-match"


def test_get_update_delete_roundtrip(client: TestClient) -> None:
    created = _create(client, name="Draft")
    project_id = created["id"]

    fetched = client.get(f"/api/v1/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Draft"

    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Final", "fps": 60, "state_json": '{"step": 3}'},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["name"] == "Final"
    assert body["fps"] == 60
    assert body["state_json"] == '{"step": 3}'
    assert body["sport"] == "bodybuilding"  # untouched fields survive

    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 404


def test_missing_project_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/projects/nope").status_code == 404
    assert client.patch("/api/v1/projects/nope", json={"name": "x"}).status_code == 404
    assert client.delete("/api/v1/projects/nope").status_code == 404


def test_validation_rejects_bad_payload(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json={"name": ""}).status_code == 422
    assert client.post("/api/v1/projects", json={"name": "x", "fps": 0}).status_code == 422
    assert (
        client.post("/api/v1/projects", json={"name": "x", "sport": "cricket"}).status_code == 422
    )
    assert client.post("/api/v1/projects", json={"name": "x", "unknown": 1}).status_code == 422
