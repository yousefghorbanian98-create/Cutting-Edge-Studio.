# PROGRESS LEDGER — Cutting Edge v2 (protocol v2.5.1)

Legend: **GREEN** = verified with evidence in this environment ·
**PENDING-ENV** = authored and reviewed, execution requires the Owner's Windows/Rust machine ·
**BLOCKED** = cannot proceed.

Progress: **20 / 260 steps = 7.7 %** · Phase **P0** delivered.

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

## Next: P1 — Design System & UI (30 steps)
Component library on shadcn/ui primitives (Radix), 10 component states, Style Match wizard
screens, media panel with drag-drop, i18n completeness, axe-core accessibility pass.
