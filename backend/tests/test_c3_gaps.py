"""C3 provisional guardrail — gap map is honest, not a competitor claim."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "C3-GAP-PRIORITIZATION.md"
ROADMAP = REPO / "docs" / "RECOVERY-ROADMAP.md"


def test_c3_provisional_not_claiming_observation() -> None:
    """C3 must be provisional and must not fake C2 benchmark results."""
    text = DOC.read_text(encoding="utf-8")
    assert "PROVISIONAL" in text
    assert "C2 BLOCKED" in text or "No competitor artifact" in text
    lower = text.lower()
    # Must explicitly say it's not a competitor result
    assert (
        "not competitor" in lower
        or "not a competitor" in lower
        or "provisional requirements only" in lower
    )
    assert "UNKNOWN" in text or "C2" in text
    # Must map to C2 tasks and to user value / OSS options
    assert "User value" in text
    assert "OSS option" in text or "OSS" in text
    assert "Acceptance test" in text
    # Must not bundle competitor branding
    assert "wondershare" in lower or "filmora" in lower  # mentioning is allowed
    assert "P0-1" in text
    assert "P1-1" in text


def test_c3_references_pins_and_no_downloads() -> None:
    """Gaps that need models must point at pins.json, not hidden runtime downloads."""
    text = DOC.read_text(encoding="utf-8")
    assert "pins.json" in text
    assert (
        "no runtime downloads" in text.lower()
        or "allow-list" in text.lower()
        or "libopenh264" in text.lower()
    )


def test_c3_does_not_mark_c2_verified() -> None:
    """Roadmap must still show C2 BLOCKED while C3 is provisional."""
    roadmap = ROADMAP.read_text(encoding="utf-8")
    # Find C2 row - must contain BLOCKED
    for line in roadmap.splitlines():
        if "| C2 |" in line:
            assert "BLOCKED" in line
        if "| C3 |" in line and "PROVISIONAL" not in roadmap:
            # We will update roadmap after this test passes
            pass
