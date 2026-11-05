"""Packaged same-origin transport, resource isolation and startup receipt contract."""

import json
import socket
from pathlib import Path

import pytest
from app.__main__ import desktop_listener, main
from app.config import Settings
from app.desktop import clear_receipt, publish_receipt
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def desktop(tmp_path):
    home = tmp_path / "نصب با فاصله"
    front = home / "frontend"
    front.mkdir(parents=True)
    (front / "index.html").write_text("<h1>Cutting Edge</h1>", encoding="utf-8")
    (front / "app.js").write_text('fetch("/api/v1/health")', encoding="utf-8")
    (home / "private.txt").write_text("not public", encoding="utf-8")
    return Settings(
        home_dir=home,
        data_dir=tmp_path / "data",
        serve_frontend=True,
        log_to_file=False,
        desktop_instance_id="123-456",
        desktop_ready_file=tmp_path / "startup" / "123-456.json",
    )


def test_same_origin_mount_and_headers(desktop):
    app = create_app(desktop)
    app.state.desktop_listener_owned = True  # unit contract; subprocess gate owns a real socket
    with TestClient(app, base_url="http://127.0.0.1:8756") as client:
        assert client.get("/").text == "<h1>Cutting Edge</h1>"
        assert (
            "application/javascript" in client.get("/app.js").headers["content-type"]
            or "text/javascript" in client.get("/app.js").headers["content-type"]
        )
        assert client.get("/api/v1/health").status_code == 200
        response = client.get("/api/v1/does-not-exist")
        assert response.status_code == 404
        assert "Cutting Edge" not in response.text
        assert client.get("/private.txt").status_code == 404
        assert client.get("/%2e%2e/private.txt").status_code == 404
        assert "connect-src 'self'" in response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["x-content-type-options"] == "nosniff"
        receipt = json.loads(desktop.desktop_ready_file.read_text())
        assert receipt["instance_id"] == "123-456"
        assert receipt["home"] == str(desktop.home_dir)
        assert receipt["origin"] == "http://127.0.0.1:8756"
        assert receipt["frontend_ready"] is True
    assert not desktop.desktop_ready_file.exists()


@pytest.mark.parametrize(
    "headers",
    [
        {"host": "untrusted.example:8756"},
        {"origin": "https://untrusted.example"},
        {"sec-fetch-site": "cross-site"},
        {"origin": "null"},
        {"host": "localhost:8756"},
    ],
)
def test_managed_desktop_rejects_foreign_browser_requests(desktop, headers):
    app = create_app(desktop)
    app.state.desktop_listener_owned = True
    with TestClient(app, base_url="http://127.0.0.1:8756") as client:
        assert client.get("/api/v1/health", headers=headers).status_code == 403


def test_unmanaged_preview_accepts_proxy_host(desktop):
    settings = desktop.model_copy(update={"desktop_instance_id": None, "desktop_ready_file": None})
    with TestClient(create_app(settings), base_url="https://1422-preview.e2b.app") as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/v1/health").status_code == 200
        assert "frame-ancestors" not in client.get("/").headers["content-security-policy"]


def test_missing_built_frontend_fails_visibly(desktop):
    (desktop.home_dir / "frontend" / "index.html").unlink()
    with pytest.raises(RuntimeError, match="Built frontend is missing"):
        create_app(desktop)


def test_direct_asgi_managed_launch_cannot_publish_receipt(desktop):
    with pytest.raises(RuntimeError, match="owned listener"), TestClient(create_app(desktop)):
        pass
    assert not desktop.desktop_ready_file.exists()


@pytest.mark.parametrize("change", [{"serve_frontend": False}, {"desktop_ready_file": None}])
def test_managed_receipt_requires_complete_configuration(desktop, change):
    with pytest.raises(RuntimeError, match="owned listener"):
        publish_receipt(desktop.model_copy(update=change), listener_owned=True)


def test_receipt_write_failure_is_visible(desktop):
    desktop.desktop_ready_file.parent.write_text("not a directory")
    with pytest.raises(RuntimeError, match="cache permissions"):
        publish_receipt(desktop, listener_owned=True)


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        "x" * 4097,
        '{"version":1,"instance_id":"other","origin":"x","home":"x","frontend_ready":true}',
    ],
)
def test_cleanup_preserves_unknown_or_foreign_receipt(desktop, payload):
    target = desktop.desktop_ready_file
    target.parent.mkdir()
    target.write_text(payload)
    clear_receipt(desktop)
    assert target.read_text() == payload


def test_static_mount_does_not_follow_symlink(desktop):
    link = desktop.home_dir / "frontend" / "leak.txt"
    try:
        link.symlink_to(desktop.home_dir / "private.txt")
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")
    settings = desktop.model_copy(update={"desktop_instance_id": None, "desktop_ready_file": None})
    with TestClient(create_app(settings)) as client:
        assert client.get("/leak.txt").status_code == 404


def test_exclusive_listener_refuses_existing_service(desktop):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        settings = desktop.model_copy(update={"port": occupied.getsockname()[1]})
        with pytest.raises(SystemExit, match="port unavailable"):
            desktop_listener(settings)
    assert not desktop.desktop_ready_file.exists()


def test_listener_owns_loopback_socket(desktop):
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    with desktop_listener(desktop.model_copy(update={"port": port})) as listener:
        assert listener.getsockname() == ("127.0.0.1", port)


def test_cli_passes_owned_socket_and_settings(desktop, monkeypatch):
    import app.__main__ as entry

    monkeypatch.setattr(entry, "get_settings", lambda: desktop)
    observed = []

    class Server:
        def __init__(self, config) -> None:
            self.app = config.app

        def run(self, **kwargs: object):
            app = self.app
            assert app.state.desktop_listener_owned
            assert kwargs["sockets"][0].getsockname()[0] == "127.0.0.1"
            observed.append(app.state.settings)

    monkeypatch.setattr(entry.uvicorn, "Server", Server)
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    main(["--serve-frontend", "--port", str(port)])
    assert observed[0].port == port


def test_listener_rejects_non_ipv4_loopback(desktop):
    with pytest.raises(SystemExit, match="IPv4 loopback"):
        desktop_listener(desktop.model_copy(update={"host": "localhost"}))


def test_invalid_instance_and_port_are_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(desktop_instance_id="../arbitrary")
    with pytest.raises(ValidationError):
        Settings(port=65536)


def test_native_resource_contract_matches_backend_layout():
    """Resource maps, PyInstaller onedir and resolver agree without legacy _up_ paths."""
    root = Path(__file__).resolve().parents[2]
    conf = json.loads((root / "src-tauri" / "tauri.conf.json").read_text())
    assert conf["bundle"]["resources"]["../frontend/dist"] == "frontend"
    assert conf["bundle"]["resources"]["runtime"] == "."
    assert conf["app"]["windows"][0]["url"] == "startup.html"
    assert conf["app"]["windows"][0]["create"] is False
    spec = (root / "backend" / "packaging" / "sidecar.spec").read_text()
    assert "exclude_binaries=True" in spec
    assert "COLLECT(" in spec
    build = (root / "scripts" / "build-installer.ps1").read_text()
    assert "backend/dist/cutting-edge-backend/_internal" in build
    assert "'binaries/ffmpeg/bin'" in build
    capability = json.loads((root / "src-tauri" / "capabilities" / "default.json").read_text())
    assert not any(p.startswith("shell:") for p in capability["permissions"])
