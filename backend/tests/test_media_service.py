"""MediaService decisions: proxy need, plans, encoder detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.services.media.probe import MediaInfo
from app.services.media.service import MediaService, needs_proxy


def _info(**overrides: object) -> MediaInfo:
    base = {
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "bit_rate": 8_000_000,
        "has_audio": True,
    }
    base.update(overrides)
    return MediaInfo(**base)  # type: ignore[arg-type]


def test_needs_proxy_rules() -> None:
    assert needs_proxy(_info()) is False
    assert needs_proxy(_info(width=3840, height=2160)) is True
    assert needs_proxy(_info(bit_rate=60_000_000)) is True


def test_probe_wraps_missing_file(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    service = MediaService(settings, prober=None)
    with pytest.raises(FileNotFoundError, match="file not found"):
        service.probe(tmp_path / "missing.mp4")


def test_proxy_and_thumbnail_plans(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    from tests.fixtures import fake_ffmpeg_tree

    fake_ffmpeg_tree(settings.binaries_dir)
    service = MediaService(settings)
    source = tmp_path / "a.mp4"
    source.write_bytes(b"x")

    plan = service.proxy_plan(source, _info(), tmp_path)
    assert plan[0].endswith("ffmpeg")
    assert any("scale=" in part for part in plan)

    thumbs = service.thumbnail_plan(source, tmp_path, count=8)
    assert any("tile=8x1" in part for part in thumbs)


def test_encoder_detection_without_ffmpeg_returns_none(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    service = MediaService(settings)
    assert service.detect_h264_encoder() is None


def test_encoder_smoke_command_opens_one_frame_and_writes_nothing(tmp_path: Path) -> None:
    """The availability probe must actually open the encoder, not just list it."""
    from app.services.media.ffmpeg import encoder_smoke_command, resolve_binaries
    from tests.fixtures import fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)

    argv = encoder_smoke_command(binaries, "h264_nvenc")
    assert argv[0].endswith("ffmpeg")
    assert argv[argv.index("-c:v") + 1] == "h264_nvenc"
    # One synthetic frame, discarded: never touches user media or the filesystem.
    assert argv[argv.index("-frames:v") + 1] == "1"
    assert argv[-2:] == ["-f", "null"] or argv[-3:-1] == ["-f", "null"]
    assert "-i" in argv
    assert "lavfi" in argv


def test_listed_but_unopenable_nvenc_falls_back_to_openh264(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A build that ships NVENC on a GPU-less machine must not advertise NVENC.

    Regression guard: detection previously trusted ``ffmpeg -encoders`` alone and
    reported ``h264_nvenc`` with no NVIDIA device present, so renders failed at
    runtime with ``Cannot load libcuda.so.1``.
    """
    from app.services.media import service as service_module
    from tests.fixtures import ENCODER_LIST, fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)

    calls: list[list[str]] = []

    class _Result:
        def __init__(self, stdout: str, returncode: int) -> None:
            self.stdout = stdout
            self.returncode = returncode

    def fake_run(argv: list[str], **_kwargs: object) -> _Result:
        calls.append(argv)
        if "-encoders" in argv:
            return _Result(ENCODER_LIST, 0)
        encoder = argv[argv.index("-c:v") + 1]
        # Mimic a machine with no NVIDIA device.
        return _Result("", 1 if encoder == "h264_nvenc" else 0)

    monkeypatch.setattr(service_module, "run_command", fake_run)
    service = MediaService(settings)

    assert service.detect_h264_encoder() == "libopenh264"
    assert any("-c:v" in argv and "h264_nvenc" in argv for argv in calls), "NVENC never probed"


def test_encoder_detection_is_cached_across_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probing spawns FFmpeg, so the verdict is computed once per process."""
    from app.services.media import service as service_module
    from tests.fixtures import ENCODER_LIST, fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)
    calls: list[list[str]] = []

    class _Result:
        stdout = ENCODER_LIST
        returncode = 0

    def fake_run(argv: list[str], **_kwargs: object) -> _Result:
        calls.append(argv)
        return _Result()

    monkeypatch.setattr(service_module, "run_command", fake_run)
    service = MediaService(settings)

    assert service.detect_h264_encoder() == "h264_nvenc"
    first = len(calls)
    assert service.detect_h264_encoder() == "h264_nvenc"
    assert len(calls) == first, "detection re-probed instead of using the cache"


def test_no_usable_encoder_reports_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every candidate failing to open means no H.264 encoder, not a false positive."""
    from app.services.media import service as service_module
    from tests.fixtures import ENCODER_LIST, fake_ffmpeg_tree

    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    fake_ffmpeg_tree(settings.binaries_dir)

    class _Result:
        def __init__(self, stdout: str, returncode: int) -> None:
            self.stdout = stdout
            self.returncode = returncode

    def fake_run(argv: list[str], **_kwargs: object) -> _Result:
        if "-encoders" in argv:
            return _Result(ENCODER_LIST, 0)
        return _Result("", 1)

    monkeypatch.setattr(service_module, "run_command", fake_run)
    assert MediaService(settings).detect_h264_encoder() is None
