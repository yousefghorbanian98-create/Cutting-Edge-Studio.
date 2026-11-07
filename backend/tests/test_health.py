"""Health and settings endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_offline_and_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["offline"] is True
    assert body["version"] == "1.0.0"
    assert body["database"].endswith("cutting-edge.db")


def test_settings_endpoint_hides_unknown_values(client: TestClient) -> None:
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["language"] in {"fa", "en"}
    assert body["theme"] in {"pro", "glass", "minimal"}
    assert body["offline"] is True


def test_openapi_documents_projects(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/projects" in paths
    assert "/api/v1/health" in paths
