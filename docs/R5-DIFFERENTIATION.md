# R5 — Differentiation & Performance (lightweight)

Date: 2026-11-05 · Branch `arena/dbb53bc2-cutting-edge-studio` · Status IN PROGRESS lightweight

## Hypothesis (pre-evidence)

Reliable offline sports editing + Persian support differentiates from CapCut/Filmora
generic templates. This remains a hypothesis until task-based C2 evidence supports it — see
`docs/BENCHMARK-CONTRACT.md` P0-P3.

## Implemented gaps (OSS-only, offline)

- Sports pose: `services/sports/pose_geometry.py` + `volleyball.py` + `hype.py` (MediaPipe pose → rally/hype scoring, no cloud).
- Post polish: `services/post/templates.py` + `captions.py` + `presets.py` + `loudness.py` (SRT/ASS RTL shaping, EBU R128 loudness via FFmpeg loudnorm, no external API).
- All paths are local: no runtime downloads, no subscription/cloud, pins remain in `scripts/pins.json`.

## Acceptance gates

- Sports and post modules present and covered (>80% total coverage holds).
- Persian RTL captions render (fa i18n keys + `captions.py` bidi handling).
- No GPL encoder substitution (see R3 guardrail).
- Performance: `pytest --cov` still ≥80%; render job remains allow-listed encoders only.

Heavy benchmark (real Filmora/CapCut task timing vs ours) deferred to C2/C3 until
authorized competitor artifacts are available. No competitor code/assets redistributed.
