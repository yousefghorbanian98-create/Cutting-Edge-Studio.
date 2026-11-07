# Test plan — Cutting Edge v2 v1.0.0

Two layers: everything that can be executed **without the Owner's machine** (CI + local),
and the acceptance runs that need Windows, a GPU and real footage.

## 1. Automated gates (run on every push)

| Gate | Command | Threshold | Owner |
|---|---|---|---|
| Backend lint | `cd backend && ruff check . && ruff format --check .` | zero findings | CI `backend` |
| Backend tests | `cd backend && python -m pytest --cov=app` | 100 % pass, coverage ≥ 80 % | CI `backend` |
| Dependency audit (Py) | `pip-audit -r requirements.txt --strict` | no known vulnerabilities | CI `backend` |
| Frontend lint | `cd frontend && npm run lint` | `--max-warnings 0` | CI `frontend` |
| Frontend tests | `cd frontend && npm test` | 100 % pass | CI `frontend` |
| Frontend build | `cd frontend && npm run build` | no chunk > 500 kB | CI `frontend` |
| Dependency audit (JS) | `cd frontend && npm audit --audit-level=high` | no high/critical | CI `frontend` |
| Secrets + container scan | gitleaks, trivy (CRITICAL) | zero findings | CI `security` |
| Protocol guardrails | `pytest tests/test_hygiene.py` | zero offenders | CI `backend` |
| Installer build | `scripts/build-installer.ps1 -WithoutPinnedBinaries` | `.exe` + `.sha256` produced | CI `installer` |

Latest local run (2026-11-04):

```
backend  → 117 passed, coverage 94.10 %, ruff: All checks passed!
frontend → 108 passed (15 files), eslint clean, tsc clean, build 4 chunks (max 248 kB)
pip-audit → No known vulnerabilities found
npm audit → 0 high/critical (17 moderate, dev-only chains)
```

## 2. Guardrail suite (`backend/tests/test_hygiene.py`)

Fails the build when a protocol lock is broken:

- forbidden packages (`ultralytics`, `madmom`, `super_gradients`, Ollama-family, mmaction)
- any network call or telemetry SDK in `app/`, `frontend/src`
- `shell=True` / `os.system` process invocation
- an `except` handler without a structured log (E4 error masking)
- `libx264` / `libx265` used as an argument (GPL encoders)
- unfinished `TODO`/`FIXME` markers in shipped code
- the five JSON Schemas present and draft-07

## 3. Unit-level coverage map

| Area | Tests | What is proven |
|---|---|---|
| Settings, DB, project CRUD | `test_api*.py` | contracts, 404/409 handling, SQLite migration |
| Media | `test_media_probe/ffmpeg/progress/service/runner` | ffprobe parsing incl. rotation, encoder policy, progress blocks, argv-only subprocess, watchdog timeout |
| Inference | `test_inference` | residency (one heavy model), priority eviction, cosine/NMS math, no runtime downloads |
| Sports | `test_sports_pose/volleyball` | angle table, pose classes, rep counting, tempo, Kinetics fusion, rally detection |
| Style Match | `test_stylematch` | DNA statistics, compatibility findings, EDL build/snap/validate, five G12 metrics, preview vs final plans |
| Post | `test_post` | replay window, comparison graphs, thumbnail scoring, SRT/ASS incl. RTL, b-roll ranking, loudnorm parsing, presets, templates |
| Hygiene | `test_hygiene` | every lock listed above |

## 4. Acceptance runs on the Owner's machine (not executable here)

### 4.1 Golden Set (G12)

1. Import 10 bodybuilding clips + 1 reference.
2. Run Style Match end-to-end.
3. Score with `POST /api/v1/projects/{id}/stylematch/score`.
4. **Pass condition:** at least 3 of 5 metrics pass (KS p > 0.05, shot-type F1 ≥ 0.6,
   beat error < 100 ms, pacing r > 0.7, colour ΔE < 10).

### 4.2 Performance

| Scenario | Target | How to measure |
|---|---|---|
| Timeline scrub with 200 clips | ≥ 30 fps UI, no jank | DevTools performance trace, 20 s interaction |
| 60 s 1080×1920 export, NVENC | ≤ 60 s wall clock | stopwatch around *Render final* |
| 60 s export, openh264 fallback | ≤ 240 s | same, GPU disabled |
| Peak RAM during Style Match | < 4 GB | Task Manager, backend process |
| VRAM residency | one heavy model at a time | `nvidia-smi` during analysis |

### 4.3 Install/uninstall

1. Fresh Windows 11 VM → install → verify the app starts and the status bar goes green.
2. Create a project, import a clip, export a 5 s clip.
3. Uninstall (default: keep user data) → `%APPDATA%\CuttingEdgeV2` still present.
4. Reinstall → the project is still listed.
5. Uninstall with *Also remove user data* → the folder is gone.

### 4.4 Offline proof

Disconnect the network adapter, then repeat 4.1: every flow must work identically, and
`%APPDATA%\CuttingEdgeV2\logs\cutting-edge.log` must contain zero outbound-request entries
(the runtime has no HTTP client for remote hosts at all).

## 5. Known-limits disclosure

- ML weights are **pinned by SHA-256 in `scripts/pins.json`** but not committed to git; the
  full installer is produced on a trusted build machine with `-UpdatePins` once.
- Integration/performance numbers marked "Owner" above are deliberately **not** claimed here:
  they are measured on the target hardware and pasted into the release checklist.
