# Release notes — Cutting Edge v2 v1.0.0 (protocol v2.5.1)

First delivery. Windows x64, offline, OSS-first.

## Headline

**Style Match**: 10 clips + 1 reference → editing DNA → an applied edit that reuses the
reference's cut rhythm, shot mix, camera language, colour and beat grid. Preview first,
final render second, one click each.

## What is in the box

- **Media pipeline** — ffprobe metadata (rotation, HDR-safe colour), proxy generation,
  thumbnail strips, NVENC H.264 with openh264 fallback (GPL encoders rejected at
  construction time), progress events for every job.
- **Inference registry** — one heavy model resident at a time, priority MediaPipe > CLIP >
  YOLOX > rest, explicit `ModelUnavailable` instead of a silent download.
- **Sports rules** — bodybuilding: joint angles, pose classes, peak-contraction detection,
  rep counting (scipy peak picking), symmetry, time under tension. Volleyball: Kinetics
  fusion with pose confirmation, rally detection, court quad.
- **Style Match pipeline** — 11 stages, five JSON Schemas (draft-07), compatibility report
  with block/warn/info findings, EDL builder with beat snapping, virtual camera
  (`zoompan` on the face box) and colour transfer (`eq` + `colorbalance`).
- **Acceptance metrics** — KS test, macro F1, beat error in ms, pacing Pearson r, CIE76 ΔE,
  "pass 3 of 5" aggregator (G12).
- **Post-production** — instant replay (0.5× reverse), comparison layouts (side-by-side /
  stacked / PiP), thumbnail scoring, SRT/ASS captions with RTL, CLIP-ranked b-roll,
  two-pass loudness normalisation, five platform presets, user templates.
- **Local diagnostics** — `/api/v1/system/diagnostics` for support, never uploaded.

## Quality gates reached in this build

| Gate | Result |
|---|---|
| Backend tests | 117 passed, coverage **94.10 %** (gate 80 %) |
| Frontend tests | 108 passed (15 files) |
| Lint | ruff `--select ALL` clean, eslint `--max-warnings 0` clean |
| Type check | `tsc -b` clean |
| Dependency audit | `pip-audit` no known vulnerabilities; `npm audit` 0 high/critical |
| Guardrails | no network/telemetry, no `shell=True`, no silent `except`, no GPL encoders |

## Known limitations

1. **Not code-signed.** SmartScreen shows a warning; `docs/bypass-smartscreen.md` explains it.
2. **Light build** (the CI artifact) does not embed FFmpeg or the model weights; install the
   full build for offline use, or point `PATH` at an LGPL FFmpeg.
3. **Owner-machine numbers are pending.** The Golden-Set acceptance run, the 200-clip
   timeline trace and the export timings are listed in `docs/TEST-PLAN.md §4` and must be
   recorded on the target hardware; they are not claimed here.
4. Model weights are referenced by SHA-256 in `scripts/pins.json`; they are not stored in
   git (size + licensing). One `-UpdatePins` run on a trusted network completes them.
5. AMF/QSV hardware encode is not wired in 1.0.0 (NVIDIA only).

## Upgrade / data safety

Projects live in `%APPDATA%\CuttingEdgeV2`. Uninstall keeps them by default and asks once
before deleting. Delta updates are opt-in and off in this release.

## Thanks

Built entirely from OSS: FFmpeg (LGPL), MediaPipe, YOLOX, CLIP, faster-whisper, TransNetV2,
librosa/scipy, FastAPI, React, Tauri, PyInstaller. Full inventory: `licenses/THIRD-PARTY.md`.
