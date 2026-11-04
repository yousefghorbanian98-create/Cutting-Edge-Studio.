"""B-roll ranking with CLIP embeddings (cosine similarity, re-used from the adapters)."""

from __future__ import annotations

from typing import Any

from app.services.inference.adapters import cosine_similarity

#: Minimum similarity for a b-roll clip to be offered at all.
MIN_SIMILARITY = 0.22
#: B-roll longer than this is trimmed around its most representative second.
MAX_INSERT_SECONDS = 3.0


def rank_broll(
    prompt_embedding: list[float],
    candidates: list[dict[str, Any]],
    *,
    target_duration: float = 2.0,
    min_similarity: float = MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    """Rank user-imported b-roll clips for a narrative beat ("training", "celebration")."""
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        embedding = candidate.get("embedding")
        if not embedding:
            continue
        similarity = cosine_similarity(prompt_embedding, embedding)
        if similarity < min_similarity:
            continue
        duration = float(candidate.get("duration", 0.0))
        in_point = float(candidate.get("in_point", 0.0))
        length = min(target_duration, MAX_INSERT_SECONDS, max(0.4, duration - in_point))
        ranked.append(
            {
                "path": str(candidate.get("path", "")),
                "label": str(candidate.get("label", "")),
                "similarity": round(similarity, 4),
                "in_point": round(in_point, 3),
                "out_point": round(in_point + length, 3),
                "duration": round(length, 3),
            }
        )
    ranked.sort(key=lambda item: -item["similarity"])
    return ranked


def plan_broll_inserts(
    ranked: list[dict[str, Any]],
    *,
    timeline_duration: float,
    every_seconds: float = 12.0,
    max_inserts: int = 6,
) -> list[dict[str, Any]]:
    """Spread the best b-roll clips evenly, avoiding the first and last two seconds."""
    if not ranked or timeline_duration <= 4.0:
        return []
    usable_start = 2.0
    usable_end = max(usable_start, timeline_duration - 2.0)
    slots = min(max_inserts, max(1, int((usable_end - usable_start) // every_seconds)))
    step = (usable_end - usable_start) / slots
    inserts: list[dict[str, Any]] = []
    for index in range(min(slots, len(ranked))):
        clip = ranked[index]
        inserts.append({**clip, "timeline_start": round(usable_start + step * index, 3)})
    return inserts
