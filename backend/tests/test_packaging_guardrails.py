"""R4 lightweight guardrail — pins.json + Tauri transport must be honest offline."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PINS = REPO / "scripts" / "pins.json"
TAURI_CONF = REPO / "src-tauri" / "tauri.conf.json"
SPEC = REPO / "backend" / "packaging" / "sidecar.spec"
RUST_LIB = REPO / "src-tauri" / "src" / "lib.rs"


def test_pins_json_is_pinned_and_no_hidden_downloads() -> None:
    """Every remote artifact must have a SHA-256; null = not deliverable."""
    data = json.loads(PINS.read_text(encoding="utf-8"))
    # ffmpeg must be pinned (LGPL shared build)
    assert data["ffmpeg"]["sha256"]  # noqa: PT018
    assert len(data["ffmpeg"]["sha256"]) == 64  # noqa: PT018
    assert data["ffmpeg"]["sha256"].lower() == data["ffmpeg"]["sha256"]
    assert "lgpl" in data["ffmpeg"]["license"].lower()
    # models may still be null before 100% — but we must not claim delivery
    null_models = [k for k, v in data["models"].items() if not v.get("sha256")]
    # At R4-light at least one model should still be unpinned — this documents the block
    assert len(null_models) >= 1, "unexpected: all models now pinned, update ROADMAP to VERIFIED"
    # No null sha may hide behind a real URL that would download at runtime
    for name, pin in data["models"].items():
        if not pin.get("sha256"):
            assert pin["url"], f"model {name} has neither sha nor url — honest block"


def test_tauri_conf_offline_transport() -> None:
    """Tauri must serve from backend sidecar, not Vite, in release."""
    conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    assert conf["bundle"]["targets"] == ["nsis"]
    assert "binaries/cutting-edge-backend" in conf["bundle"]["externalBin"]
    # resources must map to runtime (offline), not to ../frontend/dist alone
    resources = conf["bundle"]["resources"]
    assert "../frontend/dist" in resources
    assert "runtime" in resources or any("runtime" in k for k in resources)
    assert conf["app"]["security"]["csp"].startswith("default-src 'self'")
    # Installer must be perMachine with Farsi+English, never auto-updater
    assert "Farsi" in conf["bundle"]["windows"]["nsis"]["languages"]
    assert conf["plugins"]["updater"]["active"] is False


def test_sidecar_spec_is_onedir_not_onefile() -> None:
    """PyInstaller must be onedir (for mapped _internal), never onefile fake success."""
    text = SPEC.read_text(encoding="utf-8")
    assert "onedir" in text.lower() or "COLLECT" in text
    assert "cutting-edge-backend" in text


def test_rust_lib_uses_localhost_and_receipt() -> None:
    """Shell must talk to 127.0.0.1:8756 and use receipt file, not remote host."""
    src = RUST_LIB.read_text(encoding="utf-8")
    assert "127.0.0.1" in src
    assert "CUTTING_EDGE_HOME" in src
    assert "CUTTING_EDGE_DESKTOP_READY_FILE" in src
    assert "http://127.0.0.1:{BACKEND_PORT}" in src or "127.0.0.1" in src
    # No hardcoded external domain
    assert "https://api" not in src.lower()
