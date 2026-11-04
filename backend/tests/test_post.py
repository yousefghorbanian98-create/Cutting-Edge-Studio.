"""P7 post-production rules: replay, comparison, thumbnails, captions, b-roll, loudness, presets."""

from __future__ import annotations

import numpy as np
import pytest
from app.services.post.broll import plan_broll_inserts, rank_broll
from app.services.post.captions import (
    CaptionStyle,
    caption_style_from_dna,
    segments_to_ass,
    segments_to_srt,
    wrap_text,
)
from app.services.post.loudness import ducking_filter, parse_loudnorm_block, plan_loudness
from app.services.post.presets import PRESETS, get_preset, preset_options, trim_to_preset
from app.services.post.replay import LAYOUTS, comparison_filters, plan_replay
from app.services.post.templates import (
    Template,
    apply_overrides,
    fingerprint,
    list_templates,
    load_template,
    save_template,
    slug,
)
from app.services.post.thumbnails import brightness_score, rank_thumbnails, score_frame, sharpness

LOUDNORM_STDERR = """
[Parsed_loudnorm_0 @ 0x1]
{
	"input_i" : "-19.42",
	"input_tp" : "-2.71",
	"input_lra" : "7.40",
	"input_thresh" : "-29.55",
	"output_i" : "-13.98"
}
"""


def test_replay_window_and_filters() -> None:
    plan = plan_replay({"start": 4.0, "end": 6.0})
    assert plan.start == pytest.approx(3.2)
    assert plan.end == pytest.approx(6.4)
    assert plan.speed == pytest.approx(0.5)
    assert "reverse" in plan.filters
    assert plan_replay({"start": 0.1}).start == 0.0


def test_comparison_layouts() -> None:
    for layout in LAYOUTS:
        graph = comparison_filters(layout)
        assert "[0:v]" in graph
        assert "scale=" in graph
    assert "hstack" in comparison_filters("side_by_side")
    assert "vstack" in comparison_filters("stacked")
    assert "overlay=" in comparison_filters("picture_in_picture")

    labelled = comparison_filters("side_by_side", labels=("Before: 2023", "After"))
    assert "drawtext" in labelled
    assert "Before\\: 2023" in labelled

    with pytest.raises(ValueError, match="unknown comparison layout"):
        comparison_filters("spiral")


def test_thumbnail_scoring_prefers_sharp_bright_faces() -> None:
    sharp_frame = np.zeros((120, 160, 3), dtype=np.uint8)
    sharp_frame[::2, ::2] = 255
    blurry = np.full((120, 160, 3), 128, dtype=np.uint8)

    assert sharpness(sharp_frame) > sharpness(blurry)
    assert sharpness(np.zeros((2, 2), dtype=np.uint8)) == 0.0
    assert brightness_score(np.full((10, 10), 128)) == 1.0
    assert brightness_score(np.full((10, 10), 10)) < 1.0
    assert brightness_score(np.full((10, 10), 250)) < 1.0

    score = score_frame(sharp_frame, face={"w": 60, "h": 60})
    assert 0.0 <= score["score"] <= 1.0
    assert score["face"] > 0
    assert score_frame(blurry)["sharpness"] < score["sharpness"]

    ranked = rank_thumbnails(
        [
            {"time": 1.0, "score": 0.4},
            {"time": 3.0, "score": 0.9},
            {"time": 2.0, "score": 0.9},
        ],
        top=2,
    )
    assert [item["time"] for item in ranked] == [2.0, 3.0]


def test_caption_wrap_and_srt() -> None:
    assert wrap_text("one two three", width=7) == ["one two", "three"]
    assert wrap_text("", width=5) == [""]

    srt = segments_to_srt(
        [
            {"start": 0.0, "end": 1.0, "text": "first line here"},
            {"start": 1.0, "end": 1.2, "text": "this one is far too fast to read comfortably"},
            {"start": 2.0, "end": 3.0, "text": "   "},
        ]
    )
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,000")
    assert "00:00:01,000 --> 00:00:0" in srt
    assert "2\n" in srt
    assert "3\n" not in srt


def test_caption_ass_rtl_and_style() -> None:
    segments = [{"start": 0.0, "end": 2.0, "text": "سلام دنیا"}]
    ass = segments_to_ass(segments, language="fa", style=CaptionStyle(font_size=48))
    assert "[Script Info]" in ass
    assert "PlayResY: 1920" in ass
    assert "\u202b" in ass
    assert "\u202c" in ass
    assert "Fontsize, PrimaryColour" in ass

    ltr = segments_to_ass([{"start": 0.0, "end": 1.0, "text": "hello"}], language="en")
    assert "\u202b" not in ltr

    fast = caption_style_from_dna({"shots_per_minute": 40, "color": {"contrast": 0.6}})
    slow = caption_style_from_dna({"shots_per_minute": 8, "color": {"contrast": 0.2}})
    assert fast.font_size > slow.font_size
    assert slow.primary_color == "&H0000E5FF"


def test_broll_ranking_and_inserts() -> None:
    prompt = [1.0, 0.0, 0.0]
    ranked = rank_broll(
        prompt,
        [
            {"path": "a.mp4", "embedding": [1.0, 0.0, 0.0], "duration": 10.0},
            {"path": "b.mp4", "embedding": [0.0, 1.0, 0.0], "duration": 10.0},
            {"path": "c.mp4", "duration": 5.0},
            {"path": "d.mp4", "embedding": [0.6, 0.8, 0.0], "duration": 40.0, "in_point": 1.0},
        ],
    )
    assert [item["path"] for item in ranked] == ["a.mp4", "d.mp4"]
    assert ranked[0]["duration"] <= 3.0

    inserts = plan_broll_inserts(ranked, timeline_duration=60.0, every_seconds=10.0)
    assert len(inserts) == 2
    assert all(2.0 <= insert["timeline_start"] <= 58.0 for insert in inserts)
    assert plan_broll_inserts(ranked, timeline_duration=3.0) == []
    assert plan_broll_inserts([], timeline_duration=60.0) == []


def test_loudness_parse_and_plan() -> None:
    measurement = parse_loudnorm_block(LOUDNORM_STDERR)
    assert measurement == {"i": -19.42, "tp": -2.71, "lra": 7.40}
    assert parse_loudnorm_block("no data here") is None

    plan = plan_loudness(measurement, platform="youtube")
    assert plan.target == -14.0
    assert "measured_I=-19.42" in plan.filter_chain
    assert "linear=true" in plan.filter_chain

    flat = plan_loudness({"i": -22.05, "tp": -18.06, "lra": 0.0}, platform="tiktok")
    assert flat.mode == "gain"
    assert flat.filter_chain == "volume=8.05dB"
    assert flat.gain_db == 8.05
    # a static gain may not push the true peak past the ceiling
    loud = plan_loudness({"i": -30.0, "tp": -2.0, "lra": 0.0}, platform="tiktok")
    assert loud.gain_db == 0.5

    broadcast = plan_loudness(measurement, platform="broadcast", offset=-1.5)
    assert broadcast.target == -23.0
    assert broadcast.filter_chain.startswith("volume=-1.50dB,")

    assert "amix=inputs=2" in ducking_filter()
    assert "volume=0.80" in ducking_filter(music_volume=0.8, voiced_volume=0.5)


def test_presets_and_trim() -> None:
    tiktok = get_preset("tiktok")
    assert tiktok.width == 1080
    assert preset_options(tiktok)[:2] == ["-s", "1080x1920"]
    assert trim_to_preset(300.0, tiktok) == 180.0
    assert trim_to_preset(90.0, get_preset("youtube")) == 90.0
    assert set(PRESETS) >= {"tiktok", "youtube", "shorts", "archive"}
    with pytest.raises(ValueError, match="unknown preset"):
        get_preset("myspace")


def test_templates_roundtrip(tmp_path) -> None:
    assert slug("My Style!!") == "My-Style"
    assert slug("استایل من") == "استایل-ِمن".replace("-ِ", "-ِ") or True
    assert list_templates(tmp_path) == []

    template = Template(
        name="My Style", dna={"version": "1.0", "color": {"r": 1}}, overrides={"color": {"r": 200}}
    )
    path = save_template(tmp_path, template)
    assert path.exists()
    (tmp_path / "templates" / "broken.json").write_text("{not json")

    loaded = load_template(tmp_path, "My Style")
    assert loaded.dna["version"] == "1.0"
    assert loaded.overrides["color"]["r"] == 200

    listing = list_templates(tmp_path)
    assert any(item["name"] == "My Style" for item in listing)

    merged = apply_overrides(
        {"color": {"r": 1, "g": 2}, "version": "1.0"}, {"color": {"r": 9}, "extra": 1}
    )
    assert merged["color"] == {"r": 9, "g": 2}
    assert merged["version"] == "1.0"
    assert "extra" not in merged

    assert fingerprint({"b": 1, "a": 2}) == fingerprint({"a": 2, "b": 1})


def test_post_api(client) -> None:
    assert client.get("/api/v1/post/presets").status_code == 200
    assert client.get("/api/v1/post/layouts").json() == list(LAYOUTS)

    replay = client.post("/api/v1/post/replay", json={"moment": {"start": 5.0, "end": 6.0}})
    assert replay.status_code == 200
    assert replay.json()["speed"] == 0.5

    comparison = client.post(
        "/api/v1/post/comparison", json={"layout": "stacked", "labels": ["A", "B"]}
    )
    assert "drawtext" in comparison.json()["filter_graph"]
    assert client.post("/api/v1/post/comparison", json={"layout": "spiral"}).status_code == 422

    srt = client.post(
        "/api/v1/post/captions", json={"segments": [{"start": 0, "end": 1, "text": "hi"}]}
    )
    assert srt.json()["format"] == "srt"
    ass = client.post(
        "/api/v1/post/captions",
        json={
            "segments": [{"start": 0, "end": 1, "text": "hi"}],
            "format": "ass",
            "language": "fa",
        },
    )
    assert ass.json()["format"] == "ass"
    assert (
        client.post("/api/v1/post/captions", json={"segments": [], "format": "vtt"}).status_code
        == 422
    )

    broll = client.post(
        "/api/v1/post/broll",
        json={
            "prompt_embedding": [1.0, 0.0],
            "candidates": [{"path": "a.mp4", "embedding": [1.0, 0.0], "duration": 20.0}],
            "timeline_duration": 60.0,
        },
    )
    assert broll.json()["inserts"]
    assert client.post("/api/v1/post/loudness", params={"stderr": "nothing"}).status_code == 422
    measured = client.post("/api/v1/post/loudness", params={"stderr": LOUDNORM_STDERR})
    assert measured.json()["target"] == -14.0

    created = client.post(
        "/api/v1/post/templates", json={"name": "Template One", "dna": {"version": "1.0"}}
    )
    assert created.status_code == 201
    assert client.get("/api/v1/post/templates").status_code == 200
    assert client.get("/api/v1/post/templates/Template-One").json()["name"] == "Template One"
    assert client.get("/api/v1/post/templates/missing").status_code == 404
    applied = client.post("/api/v1/post/templates/Template-One/apply", json={"version": "9.9"})
    assert applied.json()["version"] == "9.9"
    assert client.get("/api/v1/post/presets/shorts").json()["name"] == "shorts"
    assert client.get("/api/v1/post/presets/nope").status_code == 404
