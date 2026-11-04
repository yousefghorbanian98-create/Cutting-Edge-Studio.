# PROGRESS LEDGER — Cutting Edge v2 (protocol v2.5.1)

Legend: **GREEN** = verified with evidence in this environment ·
**PENDING-ENV** = authored and reviewed, execution requires the Owner's Windows/Rust machine ·
**BLOCKED** = cannot proceed.

Progress: **72 / 260 steps = 27.7 %** · Phases **P0, P1, P2** delivered.

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

## Next: P3 — Media Pipeline (18 steps)
FFmpeg resolver (LGPL build) + ffprobe metadata, thumbnail strips, proxy generation,
import/export contracts, progress events over the local websocket/SSE, and disk-space guards.

