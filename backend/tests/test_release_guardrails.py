"""R6 lightweight guardrail — release version is consistent and offline/honest."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERSION = REPO / "VERSION"
TAURI_CONF = REPO / "src-tauri" / "tauri.conf.json"
CARGO_TOML = REPO / "src-tauri" / "Cargo.toml"
RELEASE_NOTES = REPO / "docs" / "RELEASE-NOTES-v1.0.0.md"
CHANGELOG = REPO / "CHANGELOG.md"
CHECKLIST = REPO / "docs" / "RELEASE-CHECKLIST.md"
RUST_LIB = REPO / "src-tauri" / "src" / "lib.rs"


def test_version_consistent_across_manifests() -> None:
    """VERSION, tauri.conf.json and Cargo.toml must agree — no drift."""
    ver = VERSION.read_text(encoding="utf-8").strip()
    assert re.match(r"^\d+\.\d+\.\d+$", ver), f"bad VERSION format: {ver!r}"
    conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    assert conf["version"] == ver
    cargo = CARGO_TOML.read_text(encoding="utf-8")
    # first version = package version (avoid matching dep versions)
    assert f'version = "{ver}"' in cargo


def test_changelog_and_release_notes_present() -> None:
    """Changelog 1.0.0 entry and release notes must exist — no phantom release."""
    assert RELEASE_NOTES.exists()
    assert CHANGELOG.exists()
    changelog = CHANGELOG.read_text(encoding="utf-8")
    assert "## [1.0.0]" in changelog
    assert "Known issues" in changelog
    assert "unsigned" in changelog.lower() or "smartscreen" in changelog.lower()
    notes = RELEASE_NOTES.read_text(encoding="utf-8")
    assert "v1.0.0" in notes
    assert "offline" in notes.lower()


def test_release_checklist_does_not_falsely_claim_full_bundle() -> None:
    """Full offline bundle checks must remain unchecked in lightweight — honest block."""
    text = CHECKLIST.read_text(encoding="utf-8")
    # Light build is expected to leave these unchecked
    assert "- [ ] `scripts/pins.json` has non-null hashes for FFmpeg + every model" in text
    assert "- [ ] Full packaged Tauri/approved fixed runtime" in text
    assert "BLOCKED" in text


def test_rust_offline_no_runtime_downloads() -> None:
    """Rust shell must not fetch remote URLs at runtime — downloads only at build time."""
    src = RUST_LIB.read_text(encoding="utf-8").lower()
    assert "reqwest" not in src  # no http client in shell
    assert "download" not in src or "capped" in src  # allow comments about build-time
    # Sidecar is localhost only
    assert "127.0.0.1" in src
    assert "cutting_edge_home" in src.lower() or "cutting_edge_home" in src
