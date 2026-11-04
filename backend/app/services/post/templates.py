"""User templates: save a DNA (or a full edit recipe) and re-apply it later."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

#: Templates live in the user data dir, never inside the installer.
TEMPLATE_DIR = "templates"


@dataclass(frozen=True)
class Template:
    """Stored recipe: DNA + optional user overrides."""

    name: str
    dna: dict[str, Any]
    overrides: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "dna": self.dna, "overrides": self.overrides}


def slug(name: str) -> str:
    """Filesystem-safe id for a template name (keeps Persian letters)."""
    cleaned = "".join(
        character if character.isalnum() or character in "-_ " else "" for character in name
    ).strip()
    return (cleaned or "template").replace(" ", "-")[:48]


def save_template(root: Path, template: Template) -> Path:
    """Persist a template as pretty JSON and return its path."""
    directory = root / TEMPLATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug(template.name)}.json"
    path.write_text(json.dumps(template.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_template(root: Path, name: str) -> Template:
    """Read a template back (raises ``FileNotFoundError`` when missing)."""
    path = root / TEMPLATE_DIR / f"{slug(name)}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Template(
        name=str(payload["name"]),
        dna=dict(payload["dna"]),
        overrides=dict(payload.get("overrides", {})),
    )


def list_templates(root: Path) -> list[dict[str, Any]]:
    """Templates with their names and ids, newest first."""
    directory = root / TEMPLATE_DIR
    if not directory.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {"id": path.stem, "name": payload.get("name", path.stem), "size": path.stat().st_size}
        )
    return items


def apply_overrides(dna: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge user overrides into a stored DNA (shallow, explicit keys only)."""
    merged = dict(dna)
    for key in ("color", "transition", "audio"):
        if isinstance(overrides.get(key), dict):
            merged[key] = {**merged.get(key, {}), **overrides[key]}
    for key in ("cut_lengths", "beat_times", "shots_per_minute"):
        if key in overrides:
            merged[key] = overrides[key]
    return merged


def fingerprint(dna: dict[str, Any]) -> str:
    """Stable id for a DNA snapshot (used to deduplicate templates)."""
    canonical = json.dumps(dna, sort_keys=True, ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()[:16]
