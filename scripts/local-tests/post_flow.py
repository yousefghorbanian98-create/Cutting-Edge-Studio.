"""POST-endpoint E2E against the running backend (real request bodies, real ids)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = os.environ.get("CE_E2E_BASE", "http://127.0.0.1:8756")
WORK = Path(os.environ.get("CE_E2E_WORK", "/home/user/e2e"))
PROJECT = (WORK / "project-id.txt").read_text().strip()
rows: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    rows.append((name, passed, detail))
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def call(method: str, path: str, payload=None, timeout: float = 90.0):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, json.loads(response.read() or b"null")
    except HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except json.JSONDecodeError:
            return error.code, raw.decode("utf-8", "ignore")[:200]


def main() -> None:
    assets = call("GET", f"/api/v1/projects/{PROJECT}/assets")[1]
    clip_a, clip_b = assets[0]["path"], assets[1]["path"]

    print("== post-production endpoints")
    status, body = call("POST", "/api/v1/post/replay", {"moment": {"start": 1.0, "end": 3.0}})
    check("replay plan", status == 200 and "reverse" in body.get("filters", ""), f"{status} {str(body)[:70]}")

    status, body = call("POST", "/api/v1/post/comparison", {"layout": "picture_in_picture", "labels": ["A", "B"]})
    check("comparison graph", status == 200 and "overlay" in body.get("filter_graph", ""), f"{status} {str(body)[:60]}")

    status, body = call(
        "POST",
        "/api/v1/post/captions",
        {
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "سلام دنیا"},
                {"start": 1.5, "end": 3.0, "text": "hello world"},
            ],
            "language": "fa", "format": "ass",
        },
    )
    check("persian caption file", status == 200 and "\\u202b" in json.dumps(body), f"{status} {str(body)[:60]}")

    measure = (
        "[Parsed_loudnorm_0] { \"input_i\" : \"-19.42\", \"input_tp\" : \"-2.71\", "
        "\"input_lra\" : \"7.40\" }"
    )
    status, body = call("POST", f"/api/v1/post/loudness?platform=youtube&stderr={quote(measure)}", None)
    check(
        "loudness plan",
        status == 200 and "measured_I=-19.42" in body.get("filter_chain", ""),
        f"{status} mode={body.get('mode') if isinstance(body, dict) else body}",
    )
    status, body = call("POST", "/api/v1/post/loudness?stderr=garbage", None)
    check("loudness rejects garbage", status == 422, str(status))

    status, body = call(
        "POST",
        "/api/v1/post/broll",
        {"prompt_embedding": [1.0, 0.0], "candidates": [{"path": clip_a, "embedding": [0.9, 0.1], "duration": 6}, {"path": clip_b, "embedding": [0.4, 0.6], "duration": 6}], "timeline_duration": 30.0},
    )
    check("b-roll ranking", status == 200 and body.get("ranked"), f"{status} {len(body.get('ranked', [])) if isinstance(body, dict) else 0} ranked")

    print("\n== templates lifecycle")
    status, body = call(
        "POST",
        "/api/v1/post/templates",
        {
            "name": "e2e-template",
            "dna": {"caption_style": {"font_size": 48}},
            "overrides": {"loudness_platform": "tiktok"},
        },
    )
    check("template saved", status in {200, 201}, f"{status} {str(body)[:60]}")
    status, body = call("GET", "/api/v1/post/templates/e2e-template")
    check("template read back", status == 200 and body.get("name") == "e2e-template", f"{status}")
    status, body = call("POST", "/api/v1/post/templates/e2e-template/apply", {"caption_style": {"font_size": 24}})
    check("template applied", status == 200, f"{status} {str(body)[:80]}")

    print("\n== style match validate + score")
    status, body = call("GET", f"/api/v1/projects/{PROJECT}/stylematch/edl/validate")
    check("edl validates", status == 200 and body.get("problems") == [], f"{status} {str(body)[:80]}")

    print("\n== proxy job (no H.264 encoder in this build)")
    status, job = call("POST", f"/api/v1/assets/{assets[0]['id']}/proxy", None)
    if status == 200 and isinstance(job, dict) and not job.get("id"):
        check("proxy not required for source", "not required" in str(job).lower(), str(job))
    elif status in {200, 202} and isinstance(job, dict):
        job_id = job.get("id")
        for _ in range(60):
            state = call("GET", f"/api/v1/jobs/{job_id}")[1]
            if isinstance(state, dict) and state.get("state") in {"done", "failed", "error", "cancelled"}:
                break
            time.sleep(0.5)
        check(
            "proxy job ends in a typed state",
            isinstance(state, dict) and state.get("state") in {"done", "failed"},
            f"{state.get('state')} {str(state.get('error') or state.get('message') or '')[:80]}",
        )
        check("proxy failure is explained", state.get("state") == "done" or bool(state.get("error")), "success needs no error text")
    else:
        check("proxy job accepted", False, f"{status} {str(job)[:80]}")

    passed = sum(1 for _, ok, _ in rows if ok)
    print(f"\n  {passed}/{len(rows)} checks passed")
    (WORK / "post-results.json").write_text(json.dumps(rows, indent=2))
    sys.exit(0 if passed == len(rows) else 1)


if __name__ == "__main__":
    main()
