"""Opt-in real scdet against externally generated OWNED stimuli, never downloaded media."""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.schemas_media import AssetRead
from app.services.media.scenes import FFmpegSceneInspector


@pytest.mark.skipif(
    os.environ.get("CE_SCENE_NATIVE_TESTS") != "1",
    reason="Opt-in owned native scene stimuli not provisioned",
)
@pytest.mark.parametrize(
    ("name", "frames", "times"),
    [
        ("owned-cuts-audio-first.mp4", 120, [1, 3]),
        ("owned-static.mp4", 60, []),
        ("owned-audio-only.wav", 0, None),
    ],
)
def test_real_native_candidates_and_skips(settings, tmp_path, name, frames, times):
    settings.shot_candidates_enabled = True
    settings.home_dir = Path(os.environ["CE_SCENE_HOME"])
    settings.ensure_dirs()
    original = Path(os.environ["CE_SCENE_FIXTURES"]) / name
    path = tmp_path / ("مرجع ' [] : , =" + original.suffix)
    shutil.copy2(original, path)
    now = datetime.now(UTC)
    asset = AssetRead(
        id="native-owned",
        project_id="native-owned",
        name=name,
        path=str(path),
        role="source",
        kind="video",
        duration=4,
        fps=30,
        width=160,
        height=96,
        created_at=now,
        updated_at=now,
    )
    result = FFmpegSceneInspector(settings).inspect(asset, threading.Event(), lambda _: None)
    assert result.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    if times is None:
        assert result.status == "no-video"
        assert result.estimate is None
    else:
        assert result.status == ("candidates" if times else "no-candidates")
        assert result.estimate.frames_analyzed == frames
        assert [c.time_seconds for c in result.estimate.candidates] == times
    assert not list(settings.cache_dir.glob("scenes-*"))
