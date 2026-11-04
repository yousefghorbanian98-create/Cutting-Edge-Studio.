"""Generate owned black/white cut stimuli with an explicitly supplied LGPL test FFmpeg.

No downloads, libx264, pretrained model, third-party footage or product export path.
MPEG-4 Part 2 is a native-test stimulus, not an approved shipping encoder fallback
or a browser playback acceptance claim. Keep the generated media outside Git.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import wave
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("ffmpeg", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
wav = args.output / "owned-audio-only.wav"
with wave.open(str(wav), "wb") as output:
    output.setnchannels(1)
    output.setsampwidth(2)
    output.setframerate(22050)
    output.writeframes(bytes(2 * 22050 * 2))


def run(*options: str) -> None:
    subprocess.run([str(args.ffmpeg), "-hide_banner", "-v", "error", "-nostdin", "-y", *options], check=True)


cuts = (
    "color=black:size=160x96:rate=30:duration=1[b];"
    "color=white:size=160x96:rate=30:duration=2[w];"
    "color=black:size=160x96:rate=30:duration=1[d];"
    "[b][w][d]concat=n=3:v=1:a=0"
)
run("-i", str(wav), "-f", "lavfi", "-i", cuts, "-map", "0:a", "-map", "1:v",
    "-c:a", "aac", "-c:v", "mpeg4", "-threads", "1", "-q:v", "2", "-movflags", "+faststart",
    str(args.output / "owned-cuts-audio-first.mp4"))
run("-f", "lavfi", "-i", "color=green:size=160x96:rate=30:duration=2", "-an",
    "-c:v", "mpeg4", "-threads", "1", "-q:v", "2", "-movflags", "+faststart",
    str(args.output / "owned-static.mp4"))
print(json.dumps({"ground_truth": {"owned-cuts-audio-first.mp4": {"cuts_seconds": [1, 3], "video_stream_index": 1, "frames": 120},
                                "owned-static.mp4": {"cuts_seconds": [], "frames": 60},
                                "owned-audio-only.wav": {"video": False}},
                  "scope": "owned native scdet stimuli, not semantic/video-editor acceptance"}, indent=2))
