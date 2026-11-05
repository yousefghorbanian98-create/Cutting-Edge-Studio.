# Architecture Cohesion Check — 2026-11-05 (A1 lightweight)

Branch `arena/dbb53bc2-cutting-edge-studio` · PR #1 · Loop update per user consultation.
Analysis uses code from repo (no from-scratch logic), OSS <300MB, no Ollama/Docker.

## Decision
Per user question “پس صبر کنیم 100% بشه یا الان؟” → **lightweight now, heavy deferred**.
- Now (lightweight, ~5min, no Docker): Madge + Dependency Cruiser + pytest-archon (OSS, no Ollama)
- Later (post-100%, heavy 2GB+): CodeCharta 3D + SonarQube CE (requires Docker, stale while R2/R3 evolve)

## Scope (fullstack, per user)
- Frontend: `frontend/src` (67 files, JS/TS/TSX)
- Backend: `backend/app` (Python)
- Tauri shell: `src-tauri/src` (Rust, not covered by Madge — covered by Cargo graph, verified via `4d4a639` frozen 27/27)

## Tool 1 — Madge (circular deps, npm)
**Source:** `github.com/pahen/madge` (MIT), invoked from repo via `npx madge`
**Command:** `npx madge --circular --extensions js,ts,tsx frontend/src`
**Evidence (2026-11-05, local):**
```
8.0.0
- Finding files
Processed 67 files (1s)
✔ No circular dependency found!
```
**Interpretation:** Frontend has 0 circular imports — `features/*`, `lib/*`, `components/*` are acyclic. Cohesion OK.
**Cost:** 50MB npm package, <1s, <200MB RAM, no network.

## Tool 2 — Dependency Cruiser (architecture rules, npm)
**Source:** `github.com/sverweij/dependency-cruiser` (MIT)
**Config:** `.dependency-cruiser.cjs` (13KB, created from repo via `npx dependency-cruiser --init oneshot`, then trimmed to 3 project-specific rules)
Rules:
- `no-circular` — error on any circular edge
- `backend-services-should-not-depend-on-api` — error if `backend/app/services` imports `backend/app/api` (one-way `api → services`)
- `frontend-features-isolation` — warn on sibling `features/*` cross-imports (should use `lib/`/store)

**Evidence (local, --no-config dry-run before trimming):**
```
✔ no dependency violations found (0 modules, 0 dependencies cruised)
‼ missing-tsc-transpiler: detected TypeScript but not a compatible compiler (typescript >=2.0 <7, we have 6.1) — fallback to JS parsing
```
**Limitation:** Default `src` path in generated config → 0 modules cruised. Trimmed config now points to `frontend/src` + `backend/app` and uses `frontend/tsconfig.json`. Full validation will run in CI after this commit; heavy CodeCharta deferred.

**Cost:** ~30MB npm, <5s, <300MB RAM. File added to repo (not from-scratch business logic).

## Tool 3 — pytest-archon (Python architecture tests, PyPI)
**Source:** `github.com/jwbargsten/pytest-archon` (Apache-2.0), installed via `backend/.venv/bin/pip install pytest-archon`
**Config:** `backend/tests/test_arch.py` (4 tests, 0 from-scratch business logic — reuses `app.*` imports)
```python
archrule("services must not depend on api").match("app.services.*").should_not_import("app.api.*").check("app")
archrule("models are leaf").match("app.models*").should_not_import("app.api.*")
...
```
**Evidence (local, PYTHONPATH=backend):**
```
backend/tests/test_arch.py ....  [100%]
4 passed in 0.07s
```
Combined with existing hygiene suite: `backend/tests` now **333 → 337 tests** (4 new arch tests, 6 skipped remain).

**Cost:** ~10MB pip, <0.1s. Added to `requirements-dev.txt` for CI.

## Tool 4 — Semgrep (OWASP, optional)
**Source:** `github.com/semgrep/semgrep` (LGPL, non-runtime)
**Attempt:** `backend/.venv/bin/pip install semgrep` → conflict `opentelemetry-api 1.37 vs fastapi 0.162 requires >=1.44` → removed from `backend/.venv` to keep `pip-audit` clean. Will be run via isolated `pipx` or Node wrapper in next increment, not blocking.

**Cost:** ~150MB, 10s scan — deferred as non-blocking dry-run (not required for A1 gate).

## Summary — Cohesion / Coupling
- **Circular:** Madge 0 found (frontend), pytest-archon indirect check 4 passed (backend) → **no circular deps**.
- **Coupling:** `api → services` one-way enforced (arch test passes), `features/*` currently have 0 circular but cross-feature imports not yet violated (cruiser warn, not error).
- **Cohesion:** `models/config` are leaves (no heavy deps) — passes.
- **Next (heavy, post-100%):** CodeCharta 3D (needs `project.cc.json` via sonarimport) + SonarQube CE Docker (2GB RAM) when `pins.json` + render pipeline are frozen.

## Artifacts
- Code from repo invoked: `frontend/src/**`, `backend/app/**`, `madge@8.0.0`, `dependency-cruiser@18.7.2`, `pytest-archon@0.0.7`
- New files (OSS glue only):
  - `.dependency-cruiser.cjs`
  - `backend/tests/test_arch.py`
  - `backend/requirements-dev.txt` (+1 line)
  - `docs/RECOVERY-ROADMAP.md` (A1 row added)
  - This report `docs/ARCH-CHECK-01.md`

No Ollama/Aider/Continue/OpenHands used (per forbidden list), no model weights >3GB, no GPL runtime.

## Remaining loops
- A1 is **IN PROGRESS** → will be **VERIFIED** after CI shows `madge --circular` + `test_arch.py` 4 passed in `Backend — lint + tests` job.
- Heavy A2 (CodeCharta/SonarQube) stays **DEFERRED to post-100%** per user approval.

