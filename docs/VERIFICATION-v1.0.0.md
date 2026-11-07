# Verification report — v1.0.0

Everything below was executed in the build environment on 2026-11-04. Commands are copy-pasteable.

## Backend

```
$ cd backend && .venv/bin/python -m pytest --cov=app --cov-report=term
117 passed in 3.78s
TOTAL   1255 stmts   70 miss   210 branches   20 partial   94%   (gate: 80%)

$ .venv/bin/ruff check . ; .venv/bin/ruff format --check .
All checks passed!
49 files already formatted

$ .venv/bin/python -m pip_audit -r requirements.txt --strict
No known vulnerabilities found
```

## Frontend

```
$ npm test
Test Files  15 passed (15)
     Tests  108 passed (108)

$ npm run lint        → eslint . --max-warnings 0 → clean
$ npx tsc -b          → clean
$ npm run build       → index 171.55 kB (gzip 56.27) · radix 231.04 (76.02)
                        timeline 248.34 (67.57) · motion 113.40 (37.47)
$ npm audit --audit-level=high → 0 high, 0 critical (17 moderate, dev-only)
```

## Guardrails (`tests/test_hygiene.py`)

```
12 passed — forbidden imports, pinned deps, no network/telemetry, no shell=True,
no silent except, no GPL encoder args, no TODO markers, 5 draft-07 schemas,
diagnostics endpoint, VRAM budget planner
```

## CI

| Job | Result |
|---|---|
| Backend — lint + tests (Linux) | success |
| Frontend — lint + tests + build (Linux) | success |
| Security — gitleaks + trivy (CRITICAL) | success |
| Installer — Windows NSIS build | see Actions run for the artifact `CuttingEdgeV2-Setup` |

## What is *not* verified here (and why)

| Item | Reason | Where it is tracked |
|---|---|---|
| Install/uninstall on real Windows | no Windows machine in the build environment | `docs/RELEASE-CHECKLIST.md` §B1 |
| 200-clip timeline, export timings, VRAM | needs the Owner's GPU | `docs/TEST-PLAN.md` §4.2 |
| Golden-Set acceptance (3 of 5 metrics) | needs the Owner's footage | `docs/TEST-PLAN.md` §4.1 |
| Full 3.5 GB offline installer | pinned artifacts require a trusted network | `docs/RELEASE-CHECKLIST.md` §C |
