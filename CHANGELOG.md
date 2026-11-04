# Changelog

All notable changes to Cutting Edge v2. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## Recovery R2b1 — 2026-11-04

- Added an experimental WAV rhythm adapter calling existing ISC-licensed librosa, with real click-track/silence measurements; no new beat algorithm, API/job/UI or full R2 completion claimed.
- Reused NumPy/SciPy for numeric helpers; reject placeholder model loaders and resident-limit overflow, and reject directories as model files.
- Unified wheel runtime requirements through setuptools' dependency-file support; updated vulnerable development pytest and its asyncio plugin.
- Repaired NSIS language identifier (`Farsi`, not nonexistent `Persian.nlf`) and disabled CI gitleaks PR comments without disabling scanning.
- Verification: 227 tests with optional analysis / 94.86% coverage, base 224 + 3 explicit skips, frontend 154; see `docs/RECOVERY-R2B1-REPORT.md`. Optional/native packaging, full analysis jobs, Windows installer and release remain unaccepted.

## Recovery R2a — 2026-11-04

- Added project-scoped real-media inspection jobs using registered IDs, SHA-256, ffprobe and full FFmpeg null decode, with observed progress, cancellation, durable terminal reports and explicit restart interruption.
- Added honest decode-only UI results, missing-model notices, stale-input warnings and project-isolated polling; wizard navigation no longer implies completed analysis.
- Fixed subprocess stderr deadlock/cancellation cleanup and bounded retained output; repaired Tauri frontend hook prefixes exposed by Windows check annotations.
- Local verification: 199 backend tests (94.59%), 154 frontend tests, 26/26 actual inspection browser checks and 18/18 import/playback regression; see `docs/RECOVERY-R2A-REPORT.md`.
- **Full R2/model inference, approved BtbN Windows runtime, export and installer acceptance remain OPEN/BLOCKED.** Diagnostic source-built LGPL shared tools are not bundled or a shipping acceptance claim.

## [1.0.0] — 2026-11-04

### Added
- **P0 — Foundation**: FastAPI sidecar on loopback, SQLite projects, three themes, fa/en with
  RTL, Tauri v2 shell, packaging + installer scripts, guardrail tests.
- **P1 — Design system**: tokens, Panels, Button/Badge/Select/Switch/Tabs/Stepper/Slider,
  command palette, toasts, i18n completeness test.
- **P2 — Timeline**: math layer (snapping, ripple, timecode at 30 fps), store with 50-step
  undo/redo, `@xzdarcy/react-timeline-editor` integration, hotkeys, bookmarks, playhead.
- **P3 — Media**: ffprobe parsing, FFmpeg resolver (LGPL build only), proxy/thumbnail/export
  command builders, NVENC→openh264 policy, progress blocks, argv-only runner with watchdog
  timeout, asset API with idempotent import and job polling.
- **P4 — Inference**: residency registry with priority eviction, cosine/rank/NMS helpers,
  pinned local model paths (no runtime downloads).
- **P5 — Sports**: pose geometry (angles, pose table, peak contraction, rep counting,
  symmetry, tempo), volleyball Kinetics fusion + rally detection, hype scoring.
- **P6 — Style Match**: 11-stage pipeline, five draft-07 JSON Schemas, compatibility report,
  EDL + beat snapping, virtual camera and colour transfer filter graphs, preview/final render
  plans, five acceptance metrics with a 3-of-5 aggregator.
- **P7 — Post-production**: replay, comparison layouts, thumbnail scoring, SRT/ASS captions
  (RTL), b-roll ranking, loudness normalisation, presets, templates; UI panel with render gate.
- **P8 — Hardening**: hygiene/guardrail suite (offline, licences, error masking), VRAM budget
  planner, `/system/diagnostics`, dependency upgrades to an audit-clean set, CI pipeline
  (lint, tests, audits, secrets, installer).
- **P9 — Delivery**: NSIS installer build in CI, icons, sidecar one-file packaging, install
  guide (fa/en), quick start (fa/en), test plan, compatibility matrix, release notes.

### Known issues
- Installer is unsigned (SmartScreen warning accepted).
- CI artifact is the "light" build (no FFmpeg/models); the full build runs on a trusted
  Windows machine with `-UpdatePins`.
- Owner-machine performance and Golden-Set acceptance runs are pending (`docs/TEST-PLAN.md §4`).

[1.0.0]: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./releases/tag/v1.0.0
