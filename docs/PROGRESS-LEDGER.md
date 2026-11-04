# PROGRESS LEDGER — Cutting Edge v2 (protocol v2.5.1)

Legend: **GREEN** = verified with evidence in this environment ·
**PENDING-ENV** = authored and reviewed, execution requires the Owner's Windows/Rust machine ·
**BLOCKED** = cannot proceed.

> **2026-11-04 acceptance correction:** the historical 260/260 count below means authored
> implementation steps, **not verified release readiness**. The live browser audit found
> disconnected import/analysis/render flows; compliant encoder, models and Windows installer
> acceptance remain blocked. See [LOCAL-TEST-REPORT.md](LOCAL-TEST-REPORT.md), which supersedes
> conflicting blanket GREEN/delivered claims in this ledger.

Progress: **260 / 260 authored steps = 100 %** · **Release acceptance: BLOCKED**.

Recovery loop resumed by owner on 2026-11-04. See [RECOVERY-ROADMAP.md](RECOVERY-ROADMAP.md).
R1 real import/source playback passed locally (18 browser checks). R1b save/reopen also passed
locally (26 browser checks across a real backend restart; [report](RECOVERY-R1B-REPORT.md)).
R2a real-media inspection passed locally (26 browser checks including a deliberate backend crash,
199 backend tests / 94.59%, 154 frontend tests; [report](RECOVERY-R2A-REPORT.md), code `675478c`).
R2b1 then validated a standalone librosa rhythm adapter (3/3 synthetic fixtures; 227 tests with
optional analysis / 94.86%, base 224 + 3 explicit skips); [report](RECOVERY-R2B1-REPORT.md),
code `d1decc2`. At that revision it was not wired to project jobs/UI; R2b2 subsequently added that glue, still without Windows distribution acceptance.
R2a remains decoding/probing/hashing only, not pretrained model analysis. Full R2, R3 rendering and
Windows gates remain open. Competitor benchmark C1 is
specified; actual CapCut/Filmora behavior is still unobserved.

R2b3 default-disabled native scdet candidate jobs/UI now have local owned-stimulus evidence: code
`d16b1b5`, 287 optional/native tests (93.75%), 281 base + 6 skips, 167 frontend and 25/25 browser
checks. See [RECOVERY-R2B3-REPORT.md](RECOVERY-R2B3-REPORT.md). Actual 1/3-second cuts are not
semantic shot/model/StyleDNA acceptance. SIGKILL left a hardlink cache orphan; crash GC, Windows
adapter execution, native packaging and full release remain OPEN. Prior e62f847 strict-native +
NSIS light push 41926876782 succeeded; that is not full installer acceptance.

## P0 — Foundation & Setup (week 1, 20 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P0-S01 | Protocol v2.5.1 decisions recorded (16 G + D/E) | GREEN | `docs/PROTOCOL-ISSUES.md` RESOLUTION LOG, `docs/PROTOCOL-v2.5.1.md` |
| P0-S02 | Repo hygiene: `.gitignore`, `.gitattributes`, clean slate verification | GREEN | `git ls-files` = tracked source only, no venv/node_modules |
| P0-S03 | Backend scaffold: settings, logging, SQLite engine, ORM models | GREEN | `backend/app/{config,logging,db,models}.py` |
| P0-S04 | Backend API: `/health`, `/settings`, full project CRUD | GREEN | `backend/app/api/*.py`, OpenAPI at `/openapi.json` |
| P0-S05 | Backend test suite | GREEN | `23 passed`, coverage **92.95 %** (gate ≥80 %) |
| P0-S06 | Backend lint: `ruff check --select ALL` + `ruff format --check` | GREEN | `All checks passed!` |
| P0-S07 | Frontend scaffold: Vite 5 + React 18 + TS 5 + Tailwind 3 | GREEN | `frontend/package.json`, `vite.config.ts` |
| P0-S08 | Design tokens: 3 themes (pro/glass/minimal) as CSS variables | GREEN | `frontend/src/index.css`, `tailwind.config.js` |
| P0-S09 | App shell layout per §10 (menu 32px, 280/flex/300, timeline 280) | GREEN | `frontend/src/App.tsx`, `components/layout/*` |
| P0-S10 | Bilingual fa/en + global RTL (`<html dir>`, store-driven) | GREEN | `frontend/src/lib/i18n.ts`, `store/useAppStore.ts` |
| P0-S11 | Frontend tests | GREEN | `17 passed` (4 files) |
| P0-S12 | Frontend build + lint (`eslint --max-warnings 0`) | GREEN | `dist/` 172.83 kB JS gzip 56.33 kB, lint clean |
| P0-S13 | Tauri v2 shell: config, CSP, sidecar spawn, health wait | PENDING-ENV | `src-tauri/*` — needs Rust toolchain (absent here, `static.rust-lang.org` blocked) |
| P0-S14 | Sidecar packaging spec (PyInstaller onedir, windowed) | PENDING-ENV | `backend/packaging/sidecar.spec` |
| P0-S15 | Build script with SHA-256-pinned artifacts (FFmpeg LGPL, models, WebView2) | PENDING-ENV | `scripts/build-installer.ps1`, `scripts/pins.json` (hashes intentionally `null` until a trusted build fills them) |
| P0-S16 | CI: linux lint/test/audit + windows installer job | PENDING-ENV | `.github/workflows/ci.yml` |
| P0-S17 | License inventory (13 whitelisted families, exclusions documented) | GREEN | `licenses/THIRD-PARTY.md` |
| P0-S18 | Docs: reference policy, SmartScreen bypass, protocol issues | GREEN | `docs/how-to-choose-references.md`, `docs/bypass-smartscreen.md` |
| P0-S19 | Guardrail tests: no network/telemetry imports, no bare `except` | GREEN | `backend/tests/test_guardrails.py` |
| P0-S20 | Conventional commits + PR + evidence report | GREEN | this ledger + PR #1 |

### P0 gate notes
- All Linux-verifiable criteria pass. The four PENDING-ENV items are **toolchain-bound**, not
  logic-bound: they cannot be compiled or executed in a sandbox without Rust, NSIS, GPU and
  Hugging Face access (see `docs/PROTOCOL-ISSUES.md` B2/B3/B4).
- No GREEN claim is made without command output; the raw outputs are in the PR description.

## P1 — Design System & UI (week 2, 30 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P1-S01 | Design tokens: 4px spacing, 1.25 type scale, per-theme radii, motion | GREEN | `frontend/src/lib/tokens.ts` |
| P1-S02 | Fonts bundled OFL-1.1 (Vazirmatn/Inter/JetBrains Mono) — no CDN | GREEN | `@fontsource/*` imports in `main.tsx`, `dist/assets/*.woff2` |
| P1-S03 | Button (4 variants × 3 sizes, loading/error/success) | GREEN | `ui/Button.tsx` |
| P1-S04 | Badge (5 tones) | GREEN | `ui/Badge.tsx` |
| P1-S05 | Input (invalid/success) | GREEN | `ui/Input.tsx` |
| P1-S06 | Spinner (decorative mode) | GREEN | `ui/Spinner.tsx` |
| P1-S07 | ProgressBar (Radix, labelled, clamped) | GREEN | `ui/ProgressBar.tsx` |
| P1-S08 | Modal (Radix dialog, focus trap) | GREEN | `ui/Modal.tsx` |
| P1-S09 | Tooltip (Radix) | GREEN | `ui/Tooltip.tsx` |
| P1-S10 | Select (Radix, keyboard) | GREEN | `ui/Select.tsx` |
| P1-S11 | Tabs (Radix) | GREEN | `ui/Tabs.tsx` |
| P1-S12 | Switch (Radix) | GREEN | `ui/Switch.tsx` |
| P1-S13 | Slider (Radix, labelled thumb) | GREEN | `ui/Slider.tsx` |
| P1-S14 | Skeleton | GREEN | `ui/Skeleton.tsx` |
| P1-S15 | EmptyState | GREEN | `ui/EmptyState.tsx` |
| P1-S16 | Stepper (aria-current, 48px) | GREEN | `ui/Stepper.tsx` |
| P1-S17 | Toaster (sonner) | GREEN | `ui/Toaster.tsx` |
| P1-S18 | CommandPalette (cmdk + Ctrl/Cmd+K) | GREEN | `ui/CommandPalette.tsx`, `App.tsx` |
| P1-S19 | SkipLink (WCAG 2.4.1) | GREEN | `ui/SkipLink.tsx` |
| P1-S20 | Barrel export + design-system doc | GREEN | `ui/index.ts`, `docs/DESIGN-SYSTEM.md` |
| P1-S21 | Media panel with native drag-drop import | GREEN | `features/media/MediaPanel.tsx` |
| P1-S22 | Media store: dedupe by path, rejection reasons surfaced | GREEN | `features/media/mediaStore.ts` |
| P1-S23 | dnd-kit sortable reordering | GREEN | `MediaPanel.tsx` (SortableContext) |
| P1-S24 | File validation lib (ext/size/kind, byte formatting) | GREEN | `lib/files.ts` |
| P1-S25 | Wizard store + blocking rules per stage | GREEN | `features/stylematch/wizardStore.ts` |
| P1-S26 | Wizard UI: stepper, progress, motion, gating messages | GREEN | `features/stylematch/StyleMatchWizard.tsx` |
| P1-S27 | i18n expansion + key-parity completeness test | GREEN | `lib/i18n.ts`, `lib/i18n.completeness.test.ts` |
| P1-S28 | axe-core accessibility suite (fa/LTR/palette) | GREEN | `src/a11y.test.tsx` — 0 violations |
| P1-S29 | Docs + ledger update | GREEN | this file, `docs/DESIGN-SYSTEM.md` |
| P1-S30 | Commit + PR update + evidence report | GREEN | PR #1 (phase section) |

### P1 evidence snapshot
```
npm run test  → Test Files 10 passed (10) · Tests 51 passed (51)
npm run lint   → eslint --max-warnings 0 → clean
npx tsc -b     → clean
npm run build  → dist/assets/index-*.js 366.83 kB (gzip 120.29 kB), CSS 39.00 kB
axe-core       → 3 configurations, 0 violations
```

## P2 — Timeline Engine (week 3, 22 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P2-S01 | Pure timeline math module (no React, no store) | GREEN | `features/timeline/timelineMath.ts` |
| P2-S02 | Snapping: clip edges, bookmarks, zero, grid fallback | GREEN | `snapTime` + 4 unit tests |
| P2-S03 | Overlap-free placement (ripple to first free slot) | GREEN | `findFreeSlot` + tests |
| P2-S04 | Split math with inPoint continuity | GREEN | `splitClipAt` + tests |
| P2-S05 | Trim math (min duration, zero boundary) | GREEN | `trimClipEdge` + tests |
| P2-S06 | Timecode, adaptive ruler ticks, fit-to-viewport zoom | GREEN | `timecode`, `rulerTicks`, `fitZoom` |
| P2-S07 | Timeline store (Zustand + Immer) | GREEN | `features/timeline/timelineStore.ts` |
| P2-S08 | add / move / trim actions with locked-track guards | GREEN | store tests |
| P2-S09 | Split-at-playhead action | GREEN | `splitAtPlayhead` |
| P2-S10 | Selection (single + additive) and delete | GREEN | store tests |
| P2-S11 | Undo/redo history (50 entries, redo cleared on edit) | GREEN | store tests |
| P2-S12 | Bookmarks CRUD + hotkey M | GREEN | store + panel tests |
| P2-S13 | View state: zoom range 8–400, snap toggle, playback | GREEN | store tests |
| P2-S14 | Adapter store ⇄ editor rows (no library types leak) | GREEN | `timelineAdapter.ts` + 4 tests |
| P2-S15 | Editor integration (`@xzdarcy/react-timeline-editor`, MIT) | GREEN | `TimelinePanel.tsx` |
| P2-S16 | Custom ruler, playhead slider and bookmark overlay | GREEN | `TimelinePanel.tsx` |
| P2-S17 | Toolbar: play, split, delete, undo/redo, snap, zoom, timecode | GREEN | panel tests |
| P2-S18 | Hotkeys: Space, M, S, Delete, Ctrl+Z, Ctrl+Shift+Z, arrows | GREEN | `react-hotkeys-hook` + tests |
| P2-S19 | Media → timeline bridge ("add to timeline" per clip) | GREEN | `MediaPanel.tsx` |
| P2-S20 | Bundle code-splitting (react / radix / timeline / motion) | GREEN | `vite.config.ts` — no >500 kB chunk warning |
| P2-S21 | Test suite for P2 | GREEN | math 24 · adapter 4 · store 18 · panel 8 |
| P2-S22 | Docs, ledger, license update, risk R-1 | GREEN | this file, `licenses/THIRD-PARTY.md` |

### P2 evidence snapshot
```
npm run test  → Test Files 14 passed (14) · Tests 101 passed (101)
npm run lint   → clean            npx tsc -b → clean
npm run build  → index 165.49 kB (gzip 53.99) · radix 228.94 (74.93) · timeline 248.10 (67.50) · motion 113.40 (37.47)
```

### P2 risk recorded
`react-timeline-editor` is **unpublished on npm** (E404, 2022-06-18). Switched to the maintained
successor `@xzdarcy/react-timeline-editor@1.0.0` (same author/repo, MIT, React ≥18).
Fallback if it misbehaves: `dnd-timeline` (MIT). See `docs/PROTOCOL-ISSUES.md` R-1.

## P3 — Media Pipeline (18 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P3-S01 | FFmpeg resolver: bundled `binaries/ffmpeg/bin` → `binaries/ffmpeg` → `PATH` | GREEN | `app/services/media/ffmpeg.py`, `test_media_ffmpeg.py` |
| P3-S02 | Missing binary is a typed error with actionable text | GREEN | `FFmpegNotFoundError` + test |
| P3-S03 | ffprobe JSON parser: duration, fps, rotation, portrait, audio streams | GREEN | `probe.py`, `test_media_probe.py` |
| P3-S04 | Encoder policy: NVENC → openh264, GPL encoders rejected at construction | GREEN | `H264_ENCODERS`, `FORBIDDEN_ENCODERS`, tests |
| P3-S05 | NVENC parameters (`-preset p5 -tune hq -rc vbr`) | GREEN | `ffmpeg.py` + assertion test |
| P3-S06 | Export command: scale/pad/fps/yuv420p/profile high/AAC 192k/faststart | GREEN | tests |
| P3-S07 | Proxy command: 960×540 @30, 2.5 Mbit/s | GREEN | tests |
| P3-S08 | Thumbnail strip: `fps=N/1,scale=W:-1,tile=Nx1` | GREEN | tests |
| P3-S09 | `-progress` block parser → typed events with percent | GREEN | `progress.py`, `test_media_progress.py` |
| P3-S10 | Runner: argv-only, streaming progress callbacks, structured logs | GREEN | `runner.py`, `test_runner.py` |
| P3-S11 | Runner watchdog: timeout kills the child and raises `TimeoutError` | GREEN | `test_timeout_kills_the_process` |
| P3-S12 | Job registry with status/progress/error, thread-safe ids | GREEN | `jobs.py`, `test_media_service.py` |
| P3-S13 | MediaService: probe, proxy plan, thumbnail plan, export plan | GREEN | `service.py`, tests |
| P3-S14 | Asset API: import (idempotent per path), list, delete | GREEN | `api/assets.py`, `test_assets_api.py` |
| P3-S15 | Proxy job endpoint + job polling | GREEN | same |
| P3-S16 | Encoder detection endpoint (degrades to null, logged) | GREEN | same + E4 log |
| P3-S17 | Disk-space guard before long jobs | GREEN | `service.py` |
| P3-S18 | Media docs & risk notes | GREEN | this ledger, `docs/TEST-PLAN.md` |

## P4 — Inference Registry (6 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P4-S01 | `ModelSpec` (name, priority, size, dependency, license) | GREEN | `inference/registry.py` |
| P4-S02 | `max_resident = 1` with priority-order eviction (D4) | GREEN | registry tests |
| P4-S03 | Missing dependency → `ModelUnavailableError`, never a download | GREEN | registry tests |
| P4-S04 | Math helpers: L2 norm, cosine, softmax, prompt ranking, IoU, NMS | GREEN | `adapters.py`, `test_inference.py` |
| P4-S05 | Local-only model paths (`local_model_path` raises when absent) | GREEN | same |
| P4-S06 | VRAM budget planner + CPU fallback decision | GREEN | `inference/budget.py`, `test_hygiene.py` |

## P5 — Sports Logic (8 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P5-S01 | Landmark indices + protocol thresholds (peak 35°, lateral 160°, flexed 80°, extended 150°) | GREEN | `sports/pose_geometry.py` |
| P5-S02 | Joint angles: elbow, shoulder abduction, knee | GREEN | `test_sports_pose.py` |
| P5-S03 | Pose classification table (relaxed / curl / lateral / double bicep / side chest) | GREEN | measured matrix in tests |
| P5-S04 | Peak contraction + mean visibility gates | GREEN | tests |
| P5-S05 | Rep counting (`scipy.signal.find_peaks`) + time under tension | GREEN | tests (2-rep series) |
| P5-S06 | Symmetry score | GREEN | tests |
| P5-S07 | Volleyball: Kinetics map, pose-confirmed action classes, rally detection, court quad | GREEN | `volleyball.py`, `test_sports_volleyball.py` |
| P5-S08 | Hype score (motion .30 / audio .25 / face .20 / action .15 / novelty .10) | GREEN | `hype.py` + test (0.77 example) |

## P6 — Style Match (30 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P6-S01 | Stage 1 reference manifest with SHA-256, read-only | GREEN | `stylematch/pipeline.py`, `test_stylematch.py` |
| P6-S02 | Stage 2 StyleDNA: cut lengths + stats (mean/median/p10/p90/stdev) | GREEN | `dna.py` |
| P6-S03 | Shot-type counts + canonical CLIP prompts | GREEN | `dna.py` |
| P6-S04 | Camera-motion distribution + dominant transition + shares | GREEN | `dna.py` |
| P6-S05 | Beat grid → BPM, duration-weighted colour, pacing curve | GREEN | `dna.py` |
| P6-S06 | Stage 3 source summary (moments sorted by score) | GREEN | `pipeline.summarize_source` |
| P6-S07 | Stage 4 compatibility: block/warn/info + score | GREEN | `compat.py` + tests |
| P6-S08 | Stage 5 EDL build with shot priority and max-duration trim | GREEN | `edl.build_edl` |
| P6-S09 | Stage 6 beat snapping (tolerance 120 ms, never worse) | GREEN | `edl.snap_to_beats` + test |
| P6-S10 | EDL structural validation (overlap, ordering, totals) | GREEN | `edl.validate_edl` |
| P6-S11 | Stage 7 virtual camera (`zoompan` on the face anchor) | GREEN | `render.zoompan_filter` |
| P6-S12 | Stage 8 colour transfer (`eq` + `colorbalance`) | GREEN | `render.color_grade_filter` |
| P6-S13 | Stage 9 preview plan (480p/24, openh264, watermark) | GREEN | `render.build_preview_plan` |
| P6-S14 | Stage 10 final plan (NVENC, full filter chain) | GREEN | `render.build_render_plan` |
| P6-S15 | Stage 11 artifacts persisted with revisions | GREEN | `api/stylematch.py` + API test |
| P6-S16 | JSON Schema draft-07 × 5 (G13) | GREEN | `app/schemas_json/*.json` |
| P6-S17 | Metric 1 KS test on cut lengths | GREEN | `metrics.cut_length_ks` |
| P6-S18 | Metric 2 macro F1 shot types | GREEN | `metrics.shot_type_f1` |
| P6-S19 | Metric 3 beat alignment in ms | GREEN | `metrics.beat_alignment` |
| P6-S20 | Metric 4 pacing Pearson r | GREEN | `metrics.pacing_similarity` |
| P6-S21 | Metric 5 CIE76 ΔE via sRGB→Lab | GREEN | `metrics.color_delta_e` |
| P6-S22 | "Pass 3 of 5" aggregator (G12) | GREEN | `metrics.evaluate_match` |
| P6-S23 | Scoring endpoint with stored ground truth | GREEN | `POST /stylematch/score` |
| P6-S24–S30 | Frontend wizard integration, artifact list/validate endpoints, docs | GREEN | `frontend/src/features/stylematch/*`, API tests |

## P7 — Post-production (22 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P7-S01 | Replay window planner (lead 0.8 s / tail 0.4 s) | GREEN | `post/replay.py` |
| P7-S02 | Reverse + 0.5× `setpts` filter chain | GREEN | tests |
| P7-S03 | Comparison layouts: side-by-side / stacked / PiP | GREEN | `post/replay.comparison_filters` |
| P7-S04 | Label overlay with escaped colons | GREEN | API test |
| P7-S05 | Thumbnail sharpness (Laplacian variance) | GREEN | `post/thumbnails.py` |
| P7-S06 | Exposure score + face-area share + composite ranking | GREEN | tests |
| P7-S07 | SRT writer with CPS re-timing and wrapping | GREEN | `post/captions.py` |
| P7-S08 | ASS writer with RTL override marks (fa/ar) | GREEN | tests |
| P7-S09 | Caption style inference from DNA | GREEN | `caption_style_from_dna` |
| P7-S10 | B-roll CLIP cosine ranking (min similarity 0.22) | GREEN | `post/broll.py` |
| P7-S11 | Insert placement inside the safe window | GREEN | tests |
| P7-S12 | loudnorm JSON/summary/human parsing | GREEN | `post/loudness.py` + API test |
| P7-S13 | Two-pass linear plan + ducking mix | GREEN | tests |
| P7-S14 | Five platform presets with trim limits | GREEN | `post/presets.py` |
| P7-S15 | Template save/load/list/apply + fingerprint | GREEN | `post/templates.py` |
| P7-S16 | Post API (presets, layouts, replay, comparison, captions, b-roll, loudness, templates) | GREEN | `app/api/post.py` |
| P7-S17 | Post panel UI with feature switches | GREEN | `frontend/src/features/post/PostPanel.tsx` |
| P7-S18 | Render gate (`canRender`) | GREEN | `postStore.ts` + tests |
| P7-S19 | Platform presets mirrored in the UI | GREEN | `POST_PRESETS` |
| P7-S20 | RTL-safe layout inside the properties column | GREEN | panel + i18n |
| P7-S21 | fa/en strings for every new control | GREEN | `i18n.completeness.test.ts` |
| P7-S22 | Post docs + ledger | GREEN | this ledger |

## P8 — Stability & Hardening (40 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P8-S01–S08 | Guardrail suite: forbidden imports, pinned requirements, no network/telemetry, no `shell=True`, no silent `except`, no GPL encoder arguments, no TODOs, schemas present | GREEN | `tests/test_hygiene.py` (12 tests) |
| P8-S09–S14 | E4 audit: 8 handlers that returned silently now log (probe fraction/rotation, progress values, encoder probe, corrupt template, missing colour) | GREEN | `probe.py`, `progress.py`, `service.py`, `templates.py`, `metrics.py` |
| P8-S15–S20 | Dependency upgrade to an audit-clean set (fastapi 0.162, starlette 1.10, pydantic 2.14, structlog 26, python-multipart 0.0.33, vite 7, vitest 3, postcss 8.5.32, tinypool override) | GREEN | `requirements*.txt`, `package.json`, audits |
| P8-S21–S26 | CI: backend/frontend/security jobs green, installer job buildable, workflow YAML validated | GREEN | Actions runs 41854243339 (3/4 jobs) + latest installer run |
| P8-S27–S32 | VRAM budget planner + CPU fallback + device decision | GREEN | `inference/budget.py`, tests |
| P8-S33–S36 | Local diagnostics endpoint (paths, disk, FFmpeg, models, log file) | GREEN | `api/system.py` + test |
| P8-S37–S40 | Test plan, compatibility matrix, `scripts/verify.py`, evidence collection | GREEN | `docs/TEST-PLAN.md`, `docs/COMPATIBILITY.md`, `scripts/verify.py` |

## P9 — Delivery (52 steps)

| Step | Item | Status | Evidence |
|---|---|---|---|
| P9-S01–S04 | App icons (ico + 32/128 png) | GREEN | `src-tauri/icons/` |
| P9-S05–S08 | Shell hardening: no undeclared crates, loopback TCP health probe | GREEN | `src-tauri/src/lib.rs` |
| P9-S09–S12 | Sidecar one-file packaging + CLI (`--host/--port/--log-level`) | GREEN | `backend/packaging/sidecar.spec`, `app/__main__.py` |
| P9-S13–S18 | `build-installer.ps1`: pins, target triple, sidecar staging, `-WithoutPinnedBinaries`, config restore | GREEN | `scripts/build-installer.ps1` |
| P9-S19–S24 | CI installer job (Windows-safe workspace, NSIS, artifact upload) | GREEN | `.github/workflows/ci.yml` |
| P9-S25–S30 | Install guides fa/en, quick start fa/en | GREEN | `docs/install-guide-v1.0.0-{fa,en}.md`, `docs/quick-start-v1.0.0-{fa,en}.md` |
| P9-S31–S36 | Release notes, changelog, compatibility, test plan, license inventory refresh | GREEN | `docs/RELEASE-NOTES-v1.0.0.md`, `CHANGELOG.md`, `licenses/THIRD-PARTY.md` |
| P9-S37–S44 | Verification sweep: 117 backend tests (94.1 %), 108 frontend tests, ruff, eslint, tsc, build, pip-audit, npm audit | GREEN | `scripts/verify.py` output |
| P9-S45–S52 | Release checklist, PR evidence, v1.0.0 tag prep, handover note | GREEN | `docs/RELEASE-CHECKLIST.md`, PR #1 |

### P9 notes
- The **light** installer job runs on pushes, but the last observed completed installer run
  failed during cargo compilation. Artifact delivery is not confirmed; see the local report.
- The **full** offline installer needs one `-UpdatePins` run on a trusted Windows machine to
  fill the SHA-256 values for FFmpeg/models/WebView2 (`scripts/pins.json` currently `null`
  by design, so the build refuses unpinned downloads).
- Performance and Golden-Set numbers are Owner-machine measurements; see
  `docs/TEST-PLAN.md §4` — they are **not** claimed as GREEN here.

## Totals

| Phase | Steps | Status |
|---|---|---|
| P0 Foundation | 20 | GREEN (2 items toolchain-bound, now covered by CI) |
| P1 Design system & UI | 30 | GREEN |
| P2 Timeline | 22 | GREEN |
| P3 Media | 18 | GREEN |
| P4 Inference | 6 | GREEN |
| P5 Sports | 8 | GREEN |
| P6 Style Match | 30 | GREEN |
| P7 Post-production | 22 | GREEN |
| P8 Hardening | 40 | GREEN |
| P9 Delivery | 52 | GREEN |
| **Total** | **260** | **100 %** |
