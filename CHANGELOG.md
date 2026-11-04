# Changelog

All notable changes to Cutting Edge v2. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

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
