# ECC Full-Repository Review — 2026-11-08

> **Status:** F1–F5 are all addressed — see [`ECC-FIXES-2026-11-08.md`](./ECC-FIXES-2026-11-08.md).
> The "no correctness defect" conclusion below is **superseded**: a later review found one
> (C2, the false `h264_nvenc` report), now fixed.

Methodology: ECC `ecc@ecc` v2.2.3 reviewer rubrics (`security-reviewer`, `fastapi-reviewer`,
`python-reviewer`, `typescript-reviewer`, `react-reviewer`, `rust-reviewer`) applied against the
whole tree, combined with real execution of every static and dynamic gate the repository defines.

Scope: 24,304 lines of first-party source — `backend/` 15,090 · `frontend/src/` 6,251 ·
`scripts/` 2,673 · `src-tauri/src/` 290. Evidence directories excluded.

## 1. Gates executed

| Gate | Command | Result |
|---|---|---|
| Python lint | `ruff check .` | **pass** — all checks passed |
| Python format | `ruff format --check .` | **pass** — 113 files |
| Python types | `mypy app` | **pass** — 72 source files, 0 issues |
| Python tests | `pytest --cov=app` | **pass** — 391 passed, 6 skipped (397 collected) |
| Coverage | threshold 80% | **92.47%** |
| Python deps | `pip-audit -r requirements.txt` | **clean** |
| TS lint | `eslint . --max-warnings 0` | **pass** |
| TS build | `tsc -b && vite build` | **pass** — built in 10.39s |
| TS tests | `vitest run` | **pass** — 168/168 across 20 files |
| JS deps (prod) | `npm audit --omit=dev` | **0 vulnerabilities** |
| Architecture | `dependency-cruiser` | 0 errors, **19 warnings** |
| Secrets | manual sweep + `.gitleaks.toml` review | **none found** |
| Supply chain | `ecc security-ioc-scan` | **pass** |

Total first-party tests executed: **565**.

`pip-audit` run bare against the sandbox interpreter reports 11 CVEs in `pip` 23.0.1 and
`setuptools` 66.1.1. These are **not** project dependencies — neither appears in
`requirements.txt`. CI already scopes the gate correctly with `-r requirements.txt --strict`.
No action required.

The 8 moderate `npm audit` findings are confined to the `@typescript-eslint` chain and are
**dev-only**; `--omit=dev` returns 0. CI documents this in the step name.

## 2. Findings

### F1 — `Cargo.lock` is not committed · severity HIGH

`src-tauri/Cargo.lock` has never existed in history (`git log --all -- '**/Cargo.lock'` is empty)
and is not ignored. Four of five Rust dependencies use caret ranges:

```toml
tauri              = { version = "2",  features = [] }
tauri-plugin-shell = "=2.6.0"        # only exact pin
serde              = { version = "1", features = ["derive"] }
serde_json         = "1"
thiserror          = "2"
```

This is inconsistent with the pinning discipline applied everywhere else in the repository:

- 21 GitHub Actions pinned to full 40-character commit SHAs
- `npm ci` against a committed `package-lock.json` (3 CI uses)
- 12/12 Python dependencies pinned with `==`
- 4 SHA-256 pinned artifacts in `scripts/pins.json`
- A checksum-pinned `gitleaks` CLI with a negative-control test

Impact: the Windows NSIS installer — the artifact that ships to users — resolves fresh crate
versions on every build. Builds are not reproducible, and a compromised patch release of
`tauri`, `serde`, `serde_json` or `thiserror` enters the shipped binary silently. This directly
undercuts the delivery/evidence protocol, which depends on reproducible artifacts.

Fix: run `cargo generate-lockfile` in `src-tauri/`, commit the lockfile, and add
`--locked` to the installer build.

> Not fixable in this sandbox: `crates.io` and `static.rust-lang.org` are outside the network
> allowlist, and no Rust toolchain is installed. The lockfile must be generated on a machine
> with cargo.

### F2 — Rust has no CI quality gate · severity MEDIUM

`cargo clippy`, `cargo fmt --check`, `cargo test` and `cargo check` appear **nowhere** in
`.github/workflows/ci.yml`. The only job that installs a Rust toolchain is `installer`, whose
condition is:

```yaml
if: inputs.evidence_run == '' && (github.event_name == 'workflow_dispatch' || github.event_name == 'push')
```

`pull_request` is absent, so on a PR targeting `main` **`src-tauri/` is never compiled at all**.
On push it is compiled only as a release build — never linted, never tested.

Consequence: the one `#[test]` that exists (`src-tauri/src/readiness.rs:37`) has never run in CI.
290 lines of native shell glue — sidecar spawn, process-group cleanup, startup receipt — carry
zero automated verification.

Fix: add a Linux `cargo clippy -- -D warnings`, `cargo fmt --check` and `cargo test` job that
runs on `pull_request`.

### F3 — 18 architecture warnings never fail the build · severity LOW-MEDIUM

`dependency-cruiser` exits **0** despite 19 violations, because all are `severity: warn` and the
tool only fails on errors. CI therefore reports green while cross-feature coupling accumulates:

```
features/stylematch/StyleMatchWizard.tsx → features/workspace/workspaceStore.ts
features/stylematch/StyleMatchWizard.tsx → features/render/RenderPanel.tsx
features/stylematch/StyleMatchWizard.tsx → features/media/mediaStore.ts
features/timeline/TimelinePanel.tsx      → features/workspace/workspaceStore.ts
features/media/MediaPanel.tsx            → features/timeline/timelineStore.ts
… 13 more
```

The rule's own comment states the intent: *"features/\* should not directly import sibling
features — extract shared logic to lib/ or use store."* The guardrail is declared but not
enforced.

Fix: either promote `frontend-features-isolation` to `severity: error` after refactoring, or
pass an explicit warning budget so the count cannot grow.

### F4 — Dead code: `frontend/src/lib/tokens.ts` · severity LOW

43 lines, zero importers across the entire frontend (confirmed by grep and by the
`no-orphans-frontend` rule). Remove it, or wire it into the design-system work it was written for.

### F5 — `httpx` is a runtime dependency used only by tests · severity LOW

`httpx==0.28.1` sits in `backend/requirements.txt` (shipped), but the only reference in the tree
is `backend/tests/test_hygiene.py`. Nothing under `backend/app/` imports it.

For an offline-first sidecar that is frozen and shipped, this adds an unnecessary HTTP client to
the production dependency surface. Move it to `requirements-dev.txt`.

## 3. Verified strengths

These were actively probed, not assumed.

**The offline claim holds.** `grep` for `httpx|requests|urlopen|aiohttp` across `backend/app/`
returns nothing. No external URLs in `frontend/src`. `index.html` references only `/src/main.tsx`.
Fonts ship as bundled `@fontsource` packages (`.woff`/`.woff2` emitted into `dist/assets`). There
is exactly one `fetch()` call site, against a relative base. No telemetry, no CDN.

**Subprocess handling is textbook.** `backend/app/services/media/runner.py:81` is the only spawn
point: list-form argv, no `shell=True`, `stdin=DEVNULL`, and stderr routed to a `TemporaryFile`
with the reasoning recorded in a comment — *"A file, rather than an undrained pipe, prevents
stderr back-pressure deadlocks."* Timeout via `threading.Timer`, cooperative `cancel_event`, and
a `finally`-guaranteed reap.

**No event-loop blocking is possible.** All 63 API endpoints are declared `def`, not `async def`,
so Starlette runs them in a threadpool. For CPU-heavy ffmpeg work this is the correct choice, and
it is applied without a single exception. AST analysis for blocking calls inside coroutines found
zero.

**Network exposure is hard-bounded.** `app/__main__.py:36` refuses to start on any host other
than `127.0.0.1`, `app/desktop.py:53` validates the `Host` header, and CORS uses an explicit
origin allowlist.

**No injection surface.** Zero `eval`/`exec`/`pickle`/`yaml.load`. Zero f-string SQL. The one
`FileResponse` (`api/assets.py:240`) takes an opaque asset ID resolved through the database, with
the invariant documented in its docstring: *"callers supply asset IDs, never filesystem paths."*

**Frontend hygiene.** Zero `dangerouslySetInnerHTML`, zero `innerHTML`, zero `javascript:` URLs,
**zero `any` types**, zero stray `console.log`. `react-hooks/recommended` is active and lint runs
at `--max-warnings 0`, so exhaustive-deps is genuinely enforced.

**Rust safety.** No `unsafe` blocks. Every `unwrap()` sits inside `#[cfg(test)]`
(`readiness.rs:33`); production code uses only justified `.expect()` on genuinely infallible
operations ("serializing a string cannot fail", "fixed loopback URL").

**Secret scanning is unusually disciplined.** `.gitleaks.toml` uses exact path anchors, exact
regexes and `condition = "AND"`, carries the comment *"Do NOT exclude evidence directories or
JSON files wholesale"*, and is backed by `scripts/ci/gitleaks-exception-test.py` as a negative
control proving other values still fail.

**Zero `TODO`/`FIXME`/`HACK`/`XXX`** across all first-party source. Both `except Exception:`
blocks (`db.py:55`, `deps.py:21`) are correct rollback-and-re-raise session guards.

**Versions are consistent** at `1.0.0` across `VERSION`, `frontend/package.json`,
`backend/pyproject.toml`, `src-tauri/Cargo.toml` and `src-tauri/tauri.conf.json`.

## 4. Assessment

No correctness defect, security vulnerability or failing gate was found in the application code.
Code quality is high and unusually consistent, and the README's "release acceptance is BLOCKED"
posture is honest rather than aspirational — the blockers it names are real and are not papered
over in code.

Every finding above is about **release engineering around the Rust/desktop boundary**, which is
precisely the area the recovery roadmap already identifies as unaccepted. F1 and F2 are worth
closing before any installer is treated as a release candidate: together they mean the shipped
native binary is both unpinned and unverified.
