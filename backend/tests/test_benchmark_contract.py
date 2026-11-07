"""C1 lightweight guardrail — benchmark contract must be honest pre-observation."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs" / "BENCHMARK-CONTRACT.md"


def test_benchmark_contract_specified_before_observation() -> None:
    """Contract must enumerate targets/inputs/tasks/taxonomy before any C2 claims."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "CapCut" in text
    assert "Filmora" in text
    assert "Input set" in text
    assert "Tasks" in text
    assert "Evidence taxonomy" in text
    assert "P0" in text
    assert "P1" in text
    # Must state that observations are still unknown / blocked
    assert any(k in text for k in ("UNKNOWN", "BLOCKED"))
    # Must forbid repacks / DRM bypass / redistribution
    lower = text.lower()
    assert "no repacks" in lower or "repacks" in lower
    assert "drm" in lower
    # Must reference pins / no unpinned downloads
    assert "pins.json" in text


def test_no_competitor_branding_in_bundle() -> None:
    """Our repo must not bundle competitor binaries/assets/branding."""
    banned = ["capcut.exe", "filmora.exe", "wondershare"]
    for ban in banned:
        assert not list(REPO.rglob(ban)), f"banned competitor artifact present: {ban}"
    # Our Tauri bundle must not claim competitor targets
    tauri = (REPO / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    assert "capcut" not in tauri.lower()
    assert "filmora" not in tauri.lower()
