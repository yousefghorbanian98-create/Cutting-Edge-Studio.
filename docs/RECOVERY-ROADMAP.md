# Evidence-driven recovery loop and competitor benchmark

Date: 2026-11-04 · Branch `arena/dbb53bc2-cutting-edge-studio` · PR #1

## Decision

Resume the existing **inspect → implement OSS glue → test → collect evidence → update ledger** loop without approval stops, per the owner's instruction. Do not merge the owner's PR. Historical 260/260 authored steps are not release acceptance. `LOCAL-TEST-REPORT.md` is the baseline audit; this document tracks subsequent recovery work.

A competitor benchmark is now part of the plan, but **does not block essential product repairs**. CapCut and Wondershare Filmora are comparison targets, not sources of redistributable implementation code, models, assets or branding. No competitor artifact/version is currently supplied or installed. No competitor behavior has been inspected with REA yet; feature parity claims remain UNKNOWN.

## Ordered work queue

| ID | Work | Acceptance gate | Initial state |
|---|---|---|---|
| R1 | Real project/media import and source playback | Browser-selected bytes reach local backend; ffprobe metadata + real DB asset IDs; source preview uses ID-based, range-capable media route; errors visible, no fake success | LOCAL PASS: 18/18 live browser checks, see R1 report |
| R1b | Project/session reopening | Recover active project/media and preserve original display names; save/reopen timeline; no lost workspace on restart | OPEN |
| R2 | Honest analysis orchestration | Explicit reference selection; actual pretrained/OSS analysis jobs and progress; missing models block with actionable errors; no synthetic labels presented as inference | OPEN |
| R3 | Real edit preview/export | Actual EDL-to-render job, approved encoder probe, progress/cancel/error, playable output; no GPL encoder substitutions | OPEN |
| C1 | Competitor benchmark specification | Identical authorized inputs/tasks, version/platform/license recorded, evidence taxonomy and scoring fixed before observing products | SPECIFIED; competitor observations still UNKNOWN |
| R4 | Desktop transport and packaging | Production Tauri reaches sidecar without Vite; model/runtime hashes pinned; Windows installer boots offline | OPEN |
| C2 | Competitor observation with REA + manual task tests | Use official, authorized local installations; record actual version/hash; capture only owned test media; distinguish observed/derived/unknown | BLOCKED: competitor artifacts and Windows execution unavailable |
| C3 | Gap prioritization | Map observed competitor advantages to our tested baseline, with user value, OSS-compatible options, cost/dependencies and acceptance tests | AFTER C2; provisional requirements allowed, competitor claims not allowed |
| R5 | Differentiation and performance | Implement only prioritized gaps after working import→analysis→render; benchmark sports workflows and Persian subtitles | OPEN |
| R6 | Release acceptance | Clean Windows install/uninstall; genuine model quality; NVENC/openh264 performance; fully offline run | BLOCKED by preceding gates |

R1 source playback is **not** timeline-composited playback or rendered-preview acceptance. R2/R3 must not be marked complete because a wizard or button changes local state.

## C1 — shared benchmark contract

Targets: CapCut Desktop and Wondershare Filmora Desktop, Windows 11 x64. Exact versions/editions/build dates are TBD until official artifacts are acquired and execution is available. Do not use unofficial repacks, bypass activation/DRM, upload user media to cloud services, or install competitor software into our runtime bundle. If a task requires cloud processing, mark it separately; do not equate it to offline functionality.

Input set: ten owner-authorized bodybuilding/volleyball clips, one reference, locally supplied music, English and Persian speech, portrait and landscape mixtures. No third-party source media is committed.

Tasks and recorded outcomes:

1. Import ten sources plus reference; record elapsed time, retained metadata, duplicate/error behavior, memory and persistence.
2. Produce a 30–60 s vertical sports edit; record manual actions, moment selection, beat alignment and source coverage.
3. Match reference pacing/color/framing where available; mark manual work vs automated behavior, not marketing labels.
4. Correct cuts, trim, undo/redo, seek/play, compare audio/video synchronization.
5. Generate/edit/export English and Persian captions; inspect RTL shaping, timing, line wrapping and ASS/SRT interoperability.
6. Balance dialogue/music and normalize loudness; measure output using approved FFmpeg, not screenshots.
7. Export 1080×1920 H.264; measure duration, fps, audio, visual artifacts, runtime, peak memory, watermark/edition restrictions and offline support.
8. Save/reopen, recover from errors, disconnect network, repeat; identify subscription/cloud/model dependencies.

For every observation record: product/version/edition, artifact SHA-256, environment/GPU, input hashes, action sequence, screenshot/video or trace, result, limitations and confidence. Facts from documentation must cite source URLs and retrieval dates and are not treated as execution evidence.

REA roles: inert artifact inspection, bounded runtime observation and evidence capture. Use Playwright/manual interaction and FFmpeg measurements alongside it. Native analysis is optional and requires an available provider; REA alone does not reveal server-side models or certify quality/licensing.

## Prioritization rules

- **P0:** broken data path, lost work, fake success, invalid export, offline/security/licensing violations.
- **P1:** demonstrably high-value sports editing, accurate Persian captions, reliability, reduced manual work.
- **P2:** convenience/features with benchmark evidence and feasible OSS implementations.
- **P3:** cosmetic parity, effect counts and feature names without proven user value.

Our differentiation hypothesis is reliable offline sports editing plus Persian support, not cloning every competitor feature. This remains a hypothesis until task-based evidence supports it.

## Loop evidence

Each iteration records code commit, test/build outputs, relevant screenshot, observed failures, remaining blockers and next queue item. The fixed historical 260-step implementation ledger is kept separately; recovery progress is by acceptance gates, not a fabricated overall percentage.
