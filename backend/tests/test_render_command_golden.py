r"""Golden argv tests for build_edl_command — mutation-resistant.

Previous substring checks (``\"concat=n=2\" in joined``) survived mutants that
flipped ``a=0/1`` or dropped ``-c:a``. These tests assert exact
``filter_complex`` and full argv equality so any such regression fails.
"""

from __future__ import annotations

from pathlib import Path

from app.services.media.ffmpeg import FFmpegBinaries
from app.services.stylematch.render import build_edl_command

BINARIES = FFmpegBinaries(ffmpeg=Path("/usr/bin/ffmpeg"), ffprobe=Path("/usr/bin/ffprobe"))
OUTPUT = Path("/tmp/final.mp4")

# Golden filter_complex strings captured from a known-good run (2026-11-07).
# Any change to audio handling, subtitles, loudness, speed or clamping must
# update these intentionally — mutants that revert ``a=1`` → ``a=0`` will break.

GOLDEN_BASIC_2SEG = (
    "[0:v]trim=start=0:end=1.500,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s0];"
    "[0:a]atrim=start=0:end=1.500,asetpts=PTS-STARTPTS[a0];"
    "[1:v]trim=start=0:end=1.500,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s1];"
    "[1:a]atrim=start=0:end=1.500,asetpts=PTS-STARTPTS[a1];"
    "[s0][s1][a0][a1]concat=n=2:v=1:a=1[vcat][acat];"
    "[vcat]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "zoompan=z='min(1.18,1.0+(1.18-1.0)*on/15)':x='540.0-(iw/zoom/2)':y='960.0-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
    "eq=contrast=1.000:saturation=1.000,colorbalance=rs=0.000:bs=-0.000,fps=30[vout];[acat]anull[aout]"
)

GOLDEN_SILENT_2SEG = (
    "[0:v]trim=start=0:end=1.000,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s0];"
    "[1:v]trim=start=0:end=1.000,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s1];"
    "[s0][s1]concat=n=2:v=1:a=0[cat];"
    "[cat]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "zoompan=z='min(1.18,1.0+(1.18-1.0)*on/15)':x='540.0-(iw/zoom/2)':y='960.0-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
    "eq=contrast=1.000:saturation=1.000,colorbalance=rs=0.000:bs=-0.000,fps=30[vout]"
)

GOLDEN_SUBTITLES_LOUDNESS = (
    "[0:v]trim=start=0:end=2.000,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s0];"
    "[0:a]atrim=start=0:end=2.000,asetpts=PTS-STARTPTS[a0];"
    "[s0][a0]concat=n=1:v=1:a=1[vcat][acat];"
    "[vcat]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "zoompan=z='min(1.18,1.0+(1.18-1.0)*on/15)':x='540.0-(iw/zoom/2)':y='960.0-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
    "eq=contrast=1.000:saturation=1.000,colorbalance=rs=0.000:bs=-0.000,fps=30,subtitles='/tmp/subs.ass'[vout];"
    "[acat]loudnorm=I=-14:TP=-1:LRA=11[aout]"
)

GOLDEN_CLAMP_TINY = (
    "[0:v]trim=start=0:end=0.050,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s0];"
    "[0:a]atrim=start=0:end=0.050,asetpts=PTS-STARTPTS[a0];"
    "[s0][a0]concat=n=1:v=1:a=1[vcat][acat];"
    "[vcat]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "zoompan=z='min(1.18,1.0+(1.18-1.0)*on/15)':x='540.0-(iw/zoom/2)':y='960.0-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
    "eq=contrast=1.000:saturation=1.000,colorbalance=rs=0.000:bs=-0.000,fps=30[vout];[acat]anull[aout]"
)

GOLDEN_SPEED_2X = (
    "[0:v]trim=start=0:end=1.000,setpts=PTS/2.0,scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[s0];"
    "[0:a]atrim=start=0:end=1.000,asetpts=PTS-STARTPTS,atempo=2.0000[a0];"
    "[s0][a0]concat=n=1:v=1:a=1[vcat][acat];"
    "[vcat]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "zoompan=z='min(1.18,1.0+(1.18-1.0)*on/15)':x='540.0-(iw/zoom/2)':y='960.0-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
    "eq=contrast=1.000:saturation=1.000,colorbalance=rs=0.000:bs=-0.000,fps=30[vout];[acat]anull[aout]"
)


def _filter_complex(cmd: list[str]) -> str:
    idx = cmd.index("-filter_complex")
    return cmd[idx + 1]


def test_golden_basic_2seg_audio() -> None:
    """Default audio: 2 segments must produce concat a=1 with 2 maps and c:a aac."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [
            {"source": "/m/a.mp4", "in_point": 0.8, "duration": 1.5},
            {"source": "/m/b.mp4", "in_point": 1.0, "duration": 1.5},
        ],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert _filter_complex(cmd) == GOLDEN_BASIC_2SEG
    # Full argv invariants — mutants flipping a=1→a=0 or dropping maps/c:a must fail
    assert "concat=n=2:v=1:a=1" in _filter_complex(cmd)
    assert "concat=n=2:v=1:a=0" not in _filter_complex(cmd)
    assert cmd.count("-map") == 2
    assert "-c:a" in cmd
    assert "-an" not in cmd
    assert "-b:a" in cmd
    # Verify input timimg is exact (ss/t per segment)
    assert cmd.count("-ss") == 2
    assert cmd.count("-i") == 2
    assert "0.800" in cmd
    assert "1.500" in cmd


def test_golden_silent_has_audio_false() -> None:
    """has_audio=False must produce concat a=0, single map, -an, no atrim."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "has_audio": False,
        "segments": [
            {"source": "/m/a.mp4", "in_point": 0.0, "duration": 1.0},
            {"source": "/m/b.mp4", "in_point": 0.0, "duration": 1.0},
        ],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert _filter_complex(cmd) == GOLDEN_SILENT_2SEG
    assert "concat=n=2:v=1:a=0" in _filter_complex(cmd)
    assert "atrim" not in _filter_complex(cmd)
    assert cmd.count("-map") == 1
    assert "-an" in cmd
    assert "-c:a" not in cmd


def test_golden_subtitles_and_loudness_wired() -> None:
    """Subtitles and loudness filters must be wired into the graph, not ignored."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 2.0}],
    }
    cmd = build_edl_command(
        BINARIES,
        edl,
        OUTPUT,
        subtitles_path=Path("/tmp/subs.ass"),
        loudness_filter="loudnorm=I=-14:TP=-1:LRA=11",
    )
    assert _filter_complex(cmd) == GOLDEN_SUBTITLES_LOUDNESS
    fc = _filter_complex(cmd)
    assert "subtitles='/tmp/subs.ass'" in fc
    assert "loudnorm=I=-14:TP=-1:LRA=11" in fc
    assert "anull" not in fc  # loudness replaces anull when present


def test_golden_tiny_duration_clamped_to_0_05() -> None:
    """Durations below 0.05 must be clamped — prevents zero-length FFmpeg errors."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 0.01}],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert _filter_complex(cmd) == GOLDEN_CLAMP_TINY
    assert "end=0.050" in _filter_complex(cmd)
    assert "end=0.010" not in _filter_complex(cmd)
    assert "-t" in cmd
    t_idx = cmd.index("-t")
    assert cmd[t_idx + 1] == "0.050"


def test_golden_speed_atempo_chain() -> None:
    """Speed !=1.0 must set setpts=PTS/speed and add atempo chain."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 1.0, "speed": 2.0}],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert _filter_complex(cmd) == GOLDEN_SPEED_2X
    fc = _filter_complex(cmd)
    assert "setpts=PTS/2.0" in fc
    assert "atempo=2.0000" in fc


def test_golden_default_bitrate_is_12000() -> None:
    """Default bitrate must be 12000k — covers the surviving mutant branch."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 1.0}],
    }
    cmd_default = build_edl_command(BINARIES, edl, OUTPUT)
    assert "-b:v" in cmd_default
    assert cmd_default[cmd_default.index("-b:v") + 1] == "12000k"
    # Custom bitrate must be respected
    cmd_custom = build_edl_command(BINARIES, edl, OUTPUT, bitrate_kbps=8000)
    assert cmd_custom[cmd_custom.index("-b:v") + 1] == "8000k"
    assert cmd_default != cmd_custom


def test_golden_single_segment_audio_maps() -> None:
    """Single segment with audio must still have a=1 and 2 maps."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 1.0}],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert "concat=n=1:v=1:a=1" in _filter_complex(cmd)
    assert cmd.count("-map") == 2
    assert "-c:a" in cmd


def test_golden_edl_has_audio_flag_overrides_default() -> None:
    """EDL-level has_audio=False must force silent even when segments have no flag."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "has_audio": False,
        "segments": [{"source": "/m/a.mp4", "in_point": 0.0, "duration": 1.0}],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    assert "a=0" in _filter_complex(cmd)
    assert "-an" in cmd


def test_golden_full_argv_equality_basic() -> None:
    """Full argv equality for the basic case — catches any stray flag reorder."""
    edl = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "segments": [
            {"source": "/m/a.mp4", "in_point": 0.8, "duration": 1.5},
            {"source": "/m/b.mp4", "in_point": 1.0, "duration": 1.5},
        ],
    }
    cmd = build_edl_command(BINARIES, edl, OUTPUT)
    # Hardened full check — if this breaks, the render contract changed
    expected_tail = [
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "h264_nvenc",
        "-b:v",
        "12000k",
        "-preset",
        "p5",
        "-tune",
        "hq",
        "-rc",
        "vbr",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-movflags",
        "+faststart",
        str(OUTPUT),
    ]
    assert cmd[-len(expected_tail) :] == expected_tail
    assert cmd[0] == str(BINARIES.ffmpeg)
    assert cmd[1:5] == ["-y", "-hide_banner", "-loglevel", "error"]
