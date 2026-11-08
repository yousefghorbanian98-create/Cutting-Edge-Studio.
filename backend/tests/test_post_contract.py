"""Contract tests binding the frontend's bundled tables to the backend's owned data.

The post-production panel ships an offline fallback copy of the platform presets so it
can render before the sidecar answers. That copy is a second source of truth, so these
tests fail the build the moment the two drift — in either direction.

Scope note: this guards the *data* (ids and geometry). Visible labels stay local because
they are i18n keys resolved in the UI, not backend strings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.services.post.presets import PRESETS
from app.services.post.replay import LAYOUTS as COMPARISON_LAYOUTS

REPO = Path(__file__).resolve().parents[2]
POST_STORE = REPO / "frontend" / "src" / "store" / "postStore.ts"
POST_PANEL = REPO / "frontend" / "src" / "features" / "post" / "PostPanel.tsx"

_PRESET_RE = re.compile(
    r"\{\s*id:\s*'(?P<id>[a-z_]+)',\s*"
    r"labelKey:\s*'[^']+',\s*"
    r"width:\s*(?P<width>\d+),\s*"
    r"height:\s*(?P<height>\d+),\s*"
    r"maxSeconds:\s*(?P<max>\d+|null)\s*\}"
)


def _frontend_presets() -> dict[str, tuple[int, int, int | None]]:
    source = POST_STORE.read_text(encoding="utf-8")
    block = source.split("export const POST_PRESETS", 1)
    assert len(block) == 2, "POST_PRESETS table not found in postStore.ts"
    table = block[1].split("];", 1)[0]
    found = {
        match["id"]: (
            int(match["width"]),
            int(match["height"]),
            None if match["max"] == "null" else int(match["max"]),
        )
        for match in _PRESET_RE.finditer(table)
    }
    assert found, "no presets parsed from postStore.ts — did the table format change?"
    return found


def test_frontend_fallback_presets_match_backend_exactly() -> None:
    """Every bundled preset must agree with the backend on id and geometry."""
    frontend = _frontend_presets()
    backend = {
        name: (preset.width, preset.height, preset.max_seconds) for name, preset in PRESETS.items()
    }
    assert frontend == backend, (
        "post preset tables drifted between frontend fallback and backend.\n"
        f"frontend: {sorted(frontend.items())}\nbackend:  {sorted(backend.items())}"
    )


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_every_backend_preset_is_reachable_from_the_ui(name: str) -> None:
    """A preset the UI cannot offer is dead backend surface."""
    assert name in _frontend_presets(), f"backend preset '{name}' is missing from the UI"


def test_comparison_layouts_match_backend() -> None:
    """The layout selector must offer exactly what the backend accepts."""
    source = POST_STORE.read_text(encoding="utf-8")
    match = re.search(r"COMPARISON_LAYOUTS\s*=\s*\[(?P<body>[^\]]+)\]", source)
    assert match, "COMPARISON_LAYOUTS not found in postStore.ts"
    frontend = tuple(re.findall(r"'([a-z_]+)'", match["body"]))
    assert frontend == tuple(
        COMPARISON_LAYOUTS
    ), f"comparison layouts drifted: frontend={frontend} backend={tuple(COMPARISON_LAYOUTS)}"


def test_ui_consumes_the_backend_preset_endpoint() -> None:
    """Regression guard: the panel must fetch presets, not only ship a copy.

    The post feature previously rendered entirely from hardcoded state while nine
    working ``/api/v1/post/*`` endpoints went unused.
    """
    store = POST_STORE.read_text(encoding="utf-8")
    assert "api.postPresets" in store, "postStore no longer calls the backend preset endpoint"

    panel = POST_PANEL.read_text(encoding="utf-8")
    assert "hydrateFromBackend" in panel, "PostPanel no longer hydrates from the backend"
