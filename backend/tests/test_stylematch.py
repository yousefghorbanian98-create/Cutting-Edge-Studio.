"""Style Match pipeline: DNA, compatibility, EDL, beat snapping and G12 metrics."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from app.services.stylematch.compat import check_compatibility
from app.services.stylematch.dna import (
    bpm_from_beats,
    cut_lengths,
    cut_stats,
    dominant_transition,
    extend_beat_grid,
    extract_style_dna,
    target_cut_length,
)
from app.services.stylematch.edl import (
    build_edl,
    cut_times,
    pacing_curve,
    snap_to_beats,
    validate_edl,
)
from app.services.stylematch.metrics import (
    beat_alignment,
    color_delta_e,
    cut_length_ks,
    evaluate_match,
    pacing_similarity,
    shot_type_f1,
)
from app.services.stylematch.pipeline import (
    build_reference_manifest,
    run_pipeline,
    score_against_reference,
    summarize_source,
)
from app.services.stylematch.render import (
    build_edl_command,
    build_filter_chain,
    build_preview_plan,
    build_render_plan,
    color_grade_filter,
    concat_list_file,
    zoompan_filter,
)

REFERENCE = {
    "path": "/refs/cbum.mp4",
    "duration": 60.0,
    "fps": 30.0,
    "width": 1080,
    "height": 1920,
    "has_music": True,
    "beats": [i * 0.5 for i in range(40)],
    "shots": [
        {
            "start": 0.0,
            "end": 1.0,
            "type": "closeup",
            "motion": "static",
            "transition_out": "cut",
            "color": {"r": 110, "g": 90, "b": 80, "contrast": 0.6, "saturation": 0.55},
        },
        {
            "start": 1.0,
            "end": 2.5,
            "type": "medium",
            "motion": "zoom_in",
            "transition_out": "whip",
            "color": {"r": 120, "g": 95, "b": 85, "contrast": 0.65, "saturation": 0.6},
        },
        {
            "start": 2.5,
            "end": 3.3,
            "type": "closeup",
            "motion": "pan",
            "transition_out": "cut",
            "color": {"r": 105, "g": 88, "b": 78, "contrast": 0.62, "saturation": 0.5},
        },
        {
            "start": 3.3,
            "end": 4.9,
            "type": "wide",
            "motion": "static",
            "transition_out": "fade",
            "color": {"r": 100, "g": 85, "b": 75, "contrast": 0.58, "saturation": 0.52},
        },
    ],
}

SOURCE = {
    "has_audio": True,
    "clips": [
        {
            "path": "/media/a.mp4",
            "name": "a.mp4",
            "duration": 20.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "faces": True,
            "moments": [
                {
                    "start": 2.0,
                    "end": 4.0,
                    "score": 0.9,
                    "shot_type": "closeup",
                    "kind": "peak_contraction",
                },
                {"start": 8.0, "end": 10.0, "score": 0.6, "shot_type": "medium", "kind": "generic"},
            ],
        },
        {
            "path": "/media/b.mp4",
            "name": "b.mp4",
            "duration": 15.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "faces": False,
            "moments": [
                {"start": 1.0, "end": 3.0, "score": 0.75, "shot_type": "detail", "kind": "generic"}
            ],
        },
        {
            "path": "/media/c.mp4",
            "name": "c.mp4",
            "duration": 12.0,
            "width": 1920,
            "height": 1080,
            "faces": False,
        },
    ],
}


def test_dna_statistics_and_transitions() -> None:
    dna = extract_style_dna(REFERENCE)
    assert dna["reference"]["shot_count"] == 4
    assert dna["cut_lengths"] == [1.0, 1.5, 0.8, 1.6]
    assert dna["cut_stats"]["mean"] == pytest.approx(1.225)
    assert dna["shot_type_counts"]["closeup"] == 2
    assert dna["transition"]["dominant"] == "cut"
    assert dna["shots_per_minute"] == pytest.approx(4.0)
    assert dna["bpm"] == pytest.approx(120.0)
    assert dna["color"]["r"] == pytest.approx(108.98, abs=0.2)
    assert len(dna["pacing_curve"]) == 12


def test_dna_edge_cases() -> None:
    assert cut_lengths([]) == []
    assert cut_stats([])["count"] == 0.0
    assert dominant_transition([])["dominant"] == "cut"
    assert bpm_from_beats([1.0]) == 0.0
    empty = extract_style_dna({})
    assert empty["cut_stats"]["mean"] == 0.0
    assert target_cut_length(empty) == 2.0
    assert target_cut_length(extract_style_dna(REFERENCE)) > 0


def test_beat_grid_extends_past_the_reference() -> None:
    beats = [0.0, 0.5, 1.0, 1.5]
    extended = extend_beat_grid(beats, 4.0)
    assert extended[:4] == beats
    assert extended[-1] == pytest.approx(4.0)
    assert all(abs(b - a - 0.5) < 1e-6 for a, b in itertools.pairwise(extended))
    # nothing to do when the request already fits
    assert extend_beat_grid(beats, 1.0) == beats
    assert extend_beat_grid([], 10.0) == []
    assert extend_beat_grid([2.0], 10.0) == [2.0]
    assert len(extend_beat_grid(beats, 10_000.0, max_beats=6)) == 6


def test_snapping_covers_edits_longer_than_the_reference() -> None:
    dna = extract_style_dna(REFERENCE)
    edl = build_edl(dna, summarize_source(SOURCE), max_duration=1.25)
    long_edl = {**edl, "total_duration": 40.0, "segments": [*edl["segments"]] * 20}
    for index, segment in enumerate(long_edl["segments"]):
        long_edl["segments"][index] = {
            **segment,
            "timeline_start": round(index * 1.0, 3),
        }
    snapped = snap_to_beats(long_edl, list(dna["beat_times"]))
    assert snapped["segments"][-1]["timeline_start"] > dna["beat_times"][-1]


def test_edl_pacing_curve_is_comparable_to_dna() -> None:
    dna = extract_style_dna(REFERENCE)
    edl = build_edl(dna, summarize_source(SOURCE))
    curve = pacing_curve(edl, buckets=len(dna["pacing_curve"]))
    assert len(curve) == len(dna["pacing_curve"])
    assert max(curve) == 1.0
    assert all(value >= 0 for value in curve)
    assert pacing_curve({"segments": [], "total_duration": 0.0}) == []


def test_score_uses_energy_curves_not_raw_durations() -> None:
    result = run_pipeline(REFERENCE, SOURCE)
    score = score_against_reference(result.edl_v2, result.dna)
    # beat snapping must land inside the product target (100 ms), not a whole second
    alignment = score["metrics"]["beat_alignment"]
    assert alignment["value"] is not None
    assert alignment["value"] < 100.0
    assert alignment["passed"] is True
    assert score["metrics"]["pacing_similarity"]["note"] != "flat curve"


def test_compatibility_blocks_and_warns() -> None:
    dna = extract_style_dna(REFERENCE)
    blocked = check_compatibility(dna, {"clips": [{"path": "a.mp4", "duration": 10.0}]})
    assert blocked["ready"] is False
    assert any(finding["code"] == "source.too_few_clips" for finding in blocked["findings"])

    ready = check_compatibility(dna, SOURCE)
    assert ready["ready"] is True
    assert any(finding["code"] == "aspect.mismatch" for finding in ready["findings"])

    silent = check_compatibility(
        dna, {**SOURCE, "has_audio": False, "clips": [*SOURCE["clips"][:1]]}
    )
    assert any(finding["code"] == "audio.silent_source" for finding in silent["findings"])


def test_edl_build_snap_and_validate() -> None:
    dna = extract_style_dna(REFERENCE)
    source = summarize_source(SOURCE)
    edl = build_edl(dna, source)
    assert len(edl["segments"]) == 3
    assert edl["segments"][0]["source"] == "/media/a.mp4"
    assert edl["segments"][0]["duration"] == pytest.approx(1.25)
    assert validate_edl(edl) == []

    snapped = snap_to_beats(edl, list(dna["beat_times"]))
    assert snapped["version"] == "1.1"
    assert validate_edl(snapped) == []

    def mean_beat_distance(times: list[float]) -> float:
        beats = sorted(dna["beat_times"])
        return sum(min(abs(beat - time) for beat in beats) for time in times) / len(times)

    # Snapping must never move the edit further away from the grid than it already was.
    assert mean_beat_distance(cut_times(snapped)) <= mean_beat_distance(cut_times(edl)) + 1e-6

    unsnapped = snap_to_beats(edl, [])
    assert any("no beats" in note for note in unsnapped["notes"])

    limited = build_edl(dna, source, max_duration=2.0, width=1080, height=1920, fps=30)
    assert len(limited["segments"]) == 1
    assert any("max_duration" in note for note in limited["notes"])


def test_edl_without_moments_is_empty_but_valid() -> None:
    dna = extract_style_dna(REFERENCE)
    edl = build_edl(dna, {"clips": [{"path": "a.mp4", "duration": 5.0}]})
    assert edl["segments"] == []
    assert edl["total_duration"] == 0
    assert validate_edl(edl) == []
    assert any("no peak moments" in note for note in edl["notes"])


def test_full_pipeline_and_scoring() -> None:
    result = run_pipeline(REFERENCE, SOURCE)
    assert result.compatibility["ready"] is True
    assert result.edl_v2["segments"]
    assert result.problems == []

    score = score_against_reference(
        result.edl_v2,
        result.dna,
        shot_confusion={"closeup": {"closeup": 8, "medium": 2}, "medium": {"medium": 6}},
    )
    assert score["metrics"]["shot_type_f1"]["passed"] is True
    assert score["passed_count"] >= 0
    assert score["passed_count"] <= 5


def test_manifest_hashes_and_missing_files(tmp_path: Path) -> None:
    ref = tmp_path / "ref.mp4"
    ref.write_bytes(b"reference-bytes")
    manifest = build_reference_manifest(
        [ref, tmp_path / "missing.mp4"], metadata={str(ref): {"duration": 3.0}}
    )
    assert manifest["version"] == "1.0"
    assert len(manifest["files"][0]["sha256"]) == 64
    assert manifest["files"][1]["sha256"] == ""
    assert manifest["files"][0]["duration"] == 3.0


def test_metrics_pass_and_fail_paths() -> None:
    ks = cut_length_ks([1.0, 1.5, 0.8, 1.6], [1.0, 1.5, 0.9, 1.7])
    assert ks["passed"] is True
    assert cut_length_ks([], [1.0])["passed"] is False

    assert shot_type_f1({})["passed"] is False
    assert shot_type_f1({"closeup": {"closeup": 5}})["value"] > 0.99

    aligned = beat_alignment([1.0, 2.02], [1.0, 2.0])
    assert aligned["passed"] is True
    assert beat_alignment([], [1.0])["passed"] is False

    assert pacing_similarity([1, 2, 3], [1, 2, 3])["passed"] is True
    assert pacing_similarity([1, 1, 1], [1, 2, 3])["passed"] is False

    same = color_delta_e({"r": 120, "g": 90, "b": 80}, {"r": 120, "g": 90, "b": 80})
    assert same["passed"] is True
    far = color_delta_e({"r": 10, "g": 10, "b": 10}, {"r": 240, "g": 240, "b": 240})
    assert far["passed"] is False
    assert color_delta_e({}, {"r": 1, "g": 1, "b": 1})["passed"] is False

    summary = evaluate_match({"a": {"passed": True}, "b": {"passed": False}, "c": {"passed": True}})
    assert summary["passed"] is False
    assert summary["passed_count"] == 2
    assert evaluate_match({k: {"passed": True} for k in "abc"})["passed"] is True


def test_render_plans_and_filters(tmp_path: Path) -> None:
    dna = extract_style_dna(REFERENCE)
    edl = build_edl(dna, summarize_source(SOURCE))
    chain = build_filter_chain(edl, face_center=(0.4, 0.3))
    assert "zoompan" in chain
    assert "eq=" in chain
    assert "colorbalance" in chain

    zoom = zoompan_filter((0.4, 0.3), fps=30, duration=2.0, width=1080, height=1920)
    assert "zoompan=z=" in zoom
    # video input keeps 1:1 frames; only stills use `d` to hold a frame
    assert "d=1:" in zoom
    held = zoompan_filter((0.5, 0.5), fps=30, duration=2.0, still=True)
    assert "d=60:" in held
    # a portrait project must stay portrait: no hard-coded 1920x1080 canvas
    assert "s=1080x1920" in zoom
    assert "432.0-" in zoom  # 0.4 * 1080
    assert "576.0-" in zoom  # 0.3 * 1920

    grade = color_grade_filter(
        {"contrast": 0.7, "saturation": 0.8, "r": 140, "b": 90},
        {"contrast": 0.5, "saturation": 0.5},
    )
    assert "eq=contrast=" in grade
    assert "colorbalance=rs=" in grade

    from app.config import Settings
    from app.services.media.ffmpeg import resolve_binaries
    from tests.fixtures import fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "data", home_dir=tmp_path / "home", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)

    plan = build_render_plan(binaries, Path("/m/a.mp4"), Path("/out/final.mp4"), edl)
    assert plan.command[0].endswith("ffmpeg")
    assert "zoompan" in " ".join(plan.command)

    preview = build_preview_plan(binaries, Path("/m/a.mp4"), Path("/out/preview.mp4"), edl)
    assert "480" in " ".join(preview.command)
    assert "-profile:v" not in preview.command

    listing = concat_list_file(edl["segments"], tmp_path / "concat")
    assert listing.read_text().startswith("file '")


def test_edl_render_command_trims_and_concats(tmp_path: Path) -> None:
    from app.config import Settings
    from app.services.media.ffmpeg import resolve_binaries
    from tests.fixtures import fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "data", home_dir=tmp_path / "home", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)

    edl = {
        "version": "1.1",
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "total_duration": 3.0,
        "color": {"contrast": 0.6, "saturation": 0.6},
        "segments": [
            {
                "source": "/m/a.mp4",
                "in_point": 0.8,
                "out_point": 2.3,
                "timeline_start": 0.0,
                "duration": 1.5,
            },
            {
                "source": "/m/b.mp4",
                "in_point": 1.0,
                "out_point": 2.5,
                "timeline_start": 1.5,
                "duration": 1.5,
            },
        ],
    }
    command = build_edl_command(binaries, edl, tmp_path / "final.mp4")
    joined = " ".join(command)
    assert command[0].endswith("ffmpeg")
    assert command[1] == "-y"
    assert joined.count("-ss") == 2
    assert command.count("-i") == 2  # one input per segment, no stray input flags
    assert "concat=n=2:v=1:a=1" in joined
    assert "-c:a" in command
    assert "-map" in command
    assert joined.count("-map") == 2
    assert "s=1080x1920" in joined
    assert "-s" not in command
    assert "-vf" not in command
    assert command[-1] == str(tmp_path / "final.mp4")  # the output path closes the command
    assert command.count(str(tmp_path / "final.mp4")) == 1

    with pytest.raises(ValueError, match="empty EDL"):
        build_edl_command(binaries, {"segments": [], "width": 1, "height": 1}, tmp_path / "x.mp4")


def test_api_stylematch_flow(client) -> None:
    project_id = client.post("/api/v1/projects", json={"name": "SM"}).json()["id"]

    saved = client.post(
        f"/api/v1/projects/{project_id}/stylematch/reference", json={"analysis": REFERENCE}
    )
    assert saved.status_code == 201

    dna = client.post(f"/api/v1/projects/{project_id}/stylematch/dna", json={"analysis": REFERENCE})
    assert dna.status_code == 201
    assert dna.json()["cut_stats"]["count"] == 4.0

    edl = client.post(f"/api/v1/projects/{project_id}/stylematch/edl", json={"analysis": SOURCE})
    assert edl.status_code == 201, edl.text
    body = edl.json()
    assert body["edl_v2"]["segments"]
    assert body["problems"] == []

    score = client.post(
        f"/api/v1/projects/{project_id}/stylematch/score",
        json={"shot_confusion": {"closeup": {"closeup": 4}}},
    )
    assert score.status_code == 200
    assert "passed_count" in score.json()

    kinds = {
        item["kind"]
        for item in client.get(f"/api/v1/projects/{project_id}/stylematch/artifacts").json()
    }
    assert {"reference-manifest", "style-dna", "edl", "edl-v2", "match-score"} <= kinds
    assert (
        client.get(f"/api/v1/projects/{project_id}/stylematch/artifacts/style-dna").status_code
        == 200
    )
    assert client.get(f"/api/v1/projects/{project_id}/stylematch/artifacts/nope").status_code == 404
    assert (
        client.get(f"/api/v1/projects/{project_id}/stylematch/edl/validate").json()["problems"]
        == []
    )


def test_api_requires_reference_before_edl(client) -> None:
    project_id = client.post("/api/v1/projects", json={"name": "SM2"}).json()["id"]
    response = client.post(
        f"/api/v1/projects/{project_id}/stylematch/edl", json={"analysis": SOURCE}
    )
    assert response.status_code == 409
    assert client.post("/api/v1/projects/nope/stylematch/score", json={}).status_code == 404


def test_schema_files_are_valid_draft07() -> None:
    directory = Path(__file__).resolve().parents[1] / "app" / "schemas_json"
    files = sorted(directory.glob("*.schema.json"))
    assert len(files) == 5
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["$schema"].endswith("draft-07/schema#")
        assert payload["type"] == "object"
        assert payload["title"]
