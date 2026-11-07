"""End-to-end Style Match run against the live local backend (black-box over HTTP)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("CE_E2E_BASE", "http://127.0.0.1:8756") + "/api/v1"
WORK = Path(os.environ.get("CE_E2E_WORK", "/home/user/e2e"))


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict | list]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(  # noqa: S310 - loopback only
        f"{API}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            body = response.read().decode()
            return response.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode() or "{}")


def import_asset(project_id: str, path: str, role: str) -> dict:
    status, body = call("POST", f"/projects/{project_id}/assets", {"path": path, "role": role})
    if status not in (200, 201):
        raise SystemExit(f"import failed for {path}: {status} {body}")
    return body  # type: ignore[return-value]


def main() -> None:
    status, project = call("POST", "/projects", {"name": "E2E Style Match", "sport": "bodybuilding"})
    assert status == 201, project
    project_id = project["id"]  # type: ignore[index]
    print(f"project created: {project_id}")

    clips = sorted(Path("/tmp/ce-media/clips").glob("clip*.mp4"))
    for clip in clips:
        asset = import_asset(project_id, str(clip), "source")
        print(f"  import {clip.name}: {asset['width']}x{asset['height']} {asset['video_codec']}/{asset['audio_codec']} audio={asset['has_audio']}")
    reference = import_asset(project_id, "/tmp/ce-media/ref/reference.mp4", "reference")
    print(f"  import reference: {reference['duration']}s role={reference['role']}")

    reference_analysis = json.loads((WORK / "reference-analysis.json").read_text())
    source_analysis = json.loads((WORK / "source-analysis.json").read_text())

    print("\n== stage 1: reference manifest")
    status, saved = call("POST", f"/projects/{project_id}/stylematch/reference", {"analysis": reference_analysis})
    print(f"  HTTP {status} {saved}")

    print("\n== stage 2: StyleDNA")
    status, dna = call("POST", f"/projects/{project_id}/stylematch/dna", {"analysis": reference_analysis})
    print(f"  HTTP {status}")
    print(f"  cut stats: {dna['cut_stats']}")
    print(f"  shot mix:  {dna['shot_type_counts']}")
    print(f"  bpm={dna['bpm']} shots/min={dna['shots_per_minute']} transition={dna['transition']['dominant']}")
    print(f"  colour:    {dna['color']}")

    print("\n== stages 3-6: source analysis, compatibility, EDL, beat snap")
    status, body = call("POST", f"/projects/{project_id}/stylematch/edl", {"analysis": source_analysis})
    print(f"  HTTP {status}")
    edl_v2 = body["edl_v2"]
    print(f"  compatibility ready={body['compatibility']['ready']} score={body['compatibility']['score']}")
    print(f"  findings: {[f['code'] for f in body['compatibility']['findings']]}")
    print(f"  segments={len(edl_v2['segments'])} total={edl_v2['total_duration']}s")
    for segment in edl_v2["segments"][:3]:
        print(f"    {Path(segment['source']).name} in={segment['in_point']} dur={segment['duration']} at={segment['timeline_start']} type={segment['shot_type']}")
    print(f"  problems: {body['problems']}")

    print("\n== G12 metrics")
    status, score = call(
        "POST",
        f"/projects/{project_id}/stylematch/score",
        {
            "shot_confusion": {
                "closeup": {"closeup": 6, "medium": 1},
                "medium": {"medium": 5, "wide": 1},
                "wide": {"wide": 4, "detail": 1},
                "detail": {"detail": 3},
            },
        },
    )
    assert status == 200, (status, score)
    print(f"  HTTP {status} passed={score['passed']} ({score['passed_count']}/{score['required']} required)")
    for name, metric in score["metrics"].items():
        print(f"    {name:18s} passed={metric['passed']!s:5s} value={metric.get('value')}")

    print("\n== artifacts stored")
    status, artifacts = call("GET", f"/projects/{project_id}/stylematch/artifacts")
    print(f"  HTTP {status} kinds={sorted({item['kind'] for item in artifacts})}")
    status, validation = call("GET", f"/projects/{project_id}/stylematch/edl/validate")
    print(f"  edl validation: {validation}")

    (WORK / "edl-v2.json").write_text(json.dumps(edl_v2, indent=2))
    (WORK / "dna.json").write_text(json.dumps(dna, indent=2))
    (WORK / "score.json").write_text(json.dumps(score, indent=2))
    (WORK / "project-id.txt").write_text(project_id)
    print("\nwrote edl-v2.json / dna.json / score.json")


if __name__ == "__main__":
    main()
