# C3 — Gap Prioritization (provisional, pre-observation)

Date: 2026-11-05 · Branch `arena/dbb53bc2-cutting-edge-studio` · Status PROVISIONAL
Base: `docs/BENCHMARK-CONTRACT.md` (C1 VERIFIED 01c2761) · Competitor observation: C2 BLOCKED

> No competitor artifact is installed. No CapCut/Filmora behavior has been observed
> with REA. This file contains **provisional requirements only**, not benchmark
> results. Competitor claims remain UNKNOWN per `RECOVERY-ROADMAP.md`.

## Method

Map our tested baseline (R1–R6 lightweight VERIFIED) to hypothesized gaps where a
sports creator would feel value, then score by user value × OSS feasibility.
Actual competitor advantages will replace these hypotheses after C2.

## Tested baseline (what we have)

- Import 10+ clips + reference, ffprobe metadata, hash/probe jobs, progress/cancel/restart
- Audio rhythm: librosa on owned synthetic fixtures (no real-music quality claim)
- Shot candidates: scdet 1/3-second candidates, bounded native adapter
- Analysis: `InferenceRegistry` + `analysis_unavailable()` → 503 with `no runtime downloads`
- Render: EDL `segments→concat` with `filter_complex` scale/pad/zoompan/color, allow-listed encoders only (`h264_nvenc`, `libopenh264`), no GPL `libx264`
- Desktop: Tauri + sidecar on 127.0.0.1 with receipt, NSIS perMachine Farsi/English, no updater
- Differentiation: sports pose/volleyball + Persian captions + loudness (hypothesis only)

## Provisional gap map

| # | Provisional gap | User value | OSS option (licence) | Cost / dependency | Acceptance test (when real) |
|---|----------------|------------|----------------------|-------------------|-----------------------------|
| P0-1 | Genuine pretrained shot/beat quality on real sports footage | High — wrong cuts ruin edit | TransNetV2 (MIT) / librosa (ISC) already wired, need pinned weights | Download + pin in `pins.json`, Windows decode perf | C2 Task 2/4: manual correction count vs our scdet; beat error ms |
| P0-2 | NVENC real-time export vs CPU openh264 fallback | High — 60s export ≤60s | LGPL shared BtbN FFmpeg (`pins.json` pinned) `h264_nvenc` / `libopenh264` | Fixed runtime + GPU runner | C2 Task 7: wall time, fps, RAM, offline |
| P1-1 | Accurate Persian caption timing + RTL shaping | High — core hypothesis | Whisper-based (MIT) + ASS/SRT RTL helper already in `post/captions.py` | Model pin + bidi test | C2 Task 5: RTL wrap/shape, ASS interop |
| P1-2 | Dialogue/music loudness in one click | High — sports speech over music | FFmpeg `loudnorm` two-pass (LGPL) already in `post/loudness.py` | None (local) | C2 Task 6: LUFS delta via approved FFmpeg |
| P1-3 | Pose-aware hype/replay highlights | Medium — sports-specific | MediaPipe pose (Apache-2.0) already in `pose_geometry.py` | Model pin + pose accuracy | C2 Task 2: source coverage, moment selection |
| P2-1 | Template marketplace / auto-apply style | Medium | Our `post/templates.py` user presets (no cloud) | UI only | C2 Task 3: manual actions vs auto |
| P2-2 | Background download/progress UX | Low | Existing `JobRegistry` polling already | None | C2 Task 1: elapsed, memory, duplicate handling |
| P3-1 | Effect-count parity | Low | Not prioritized — P3 per rules | — | Not gated |

## Prioritization (MoSCoW for next heavy iteration)

- **Must before claim:** P0-1, P0-2, P1-1 (blocked today: need pinned models + Windows hardware + C2 observation to measure real quality/perf)
- **Should soon:** P1-2, P1-3 (code exists, needs pinned-weights smoke + Windows proof)
- **Could later:** P2-1, P2-2 (UX polish after Must is green)
- **Won't clone:** P3-1 (effect count without user value)

## What we will not do

- Install, copy, or redistribute CapCut/Filmora binaries/assets/branding.
- Bypass activation/DRM or upload user media to cloud for comparison.
- Present this provisional map as a competitor result — C2 remains BLOCKED.

## Link to acceptance gates

- Each row maps to a C2 task number and a `RECOVERY-ROADMAP.md` gate (R1–R6).
- When C2 artifacts are available, clone this file to `docs/evidence/C3-OBSERVED-*.md` and replace hypotheses with measured results (artifact SHA, env/GPU, input hashes, traces, confidence).

## References

- `docs/RECOVERY-ROADMAP.md` C3 row
- `docs/BENCHMARK-CONTRACT.md` — 8 identical tasks
- `scripts/pins.json` — honest nulls remain until trusted pin run
- `docs/R5-DIFFERENTIATION.md` — offline sports+Persian hypothesis
