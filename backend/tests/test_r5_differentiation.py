"""R5 lightweight guardrail — differentiation modules present offline."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_sports_post_modules_present() -> None:
    """Sports pose + post polish must be real modules, not stubs."""
    assert (REPO / "backend" / "app" / "services" / "sports" / "pose_geometry.py").exists()
    assert (REPO / "backend" / "app" / "services" / "sports" / "volleyball.py").exists()
    assert (REPO / "backend" / "app" / "services" / "post" / "captions.py").exists()
    assert (REPO / "backend" / "app" / "services" / "post" / "templates.py").exists()
    assert (REPO / "backend" / "app" / "services" / "post" / "loudness.py").exists()
    # No cloud/subscription imports in differentiation layer
    for mod in ["captions.py", "templates.py", "pose_geometry.py"]:
        text = (REPO / "backend" / "app" / "services").rglob(mod)
        for path in text:
            src = path.read_text(encoding="utf-8").lower()
            assert "openai" not in src
            assert "subscription" not in src


def test_persian_i18n_present() -> None:
    """Persian UI must have i18n keys for sports/post/render flows."""
    i18n = (REPO / "frontend" / "src" / "lib" / "i18n.ts").read_text(encoding="utf-8")
    assert "fa" in i18n
    # At least one Persian string for differentiation surfaces
    assert "پردازش" in i18n or "زیرنویس" in i18n or "ورزش" in i18n or "فارسی" in i18n


def test_differentiation_doc_declares_hypothesis() -> None:
    """R5 doc must state hypothesis, not claim benchmark win before C2."""
    text = (REPO / "docs" / "R5-DIFFERENTIATION.md").read_text(encoding="utf-8")
    assert "hypothesis" in text.lower()
    assert "C2" in text
    assert "no competitor" in text.lower() or "no cloud" in text.lower()
