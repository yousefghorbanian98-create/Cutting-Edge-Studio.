# Cutting Edge v2

Offline-first sports video editor (bodybuilding + volleyball) for Windows.
Target core feature: **Style Match** — analyse a reference edit's DNA and apply it to your own clips.

> **Release acceptance is BLOCKED (2026-11-05).** Real import/reopening/decode and experimental
> audio-rhythm and native cut-candidate jobs have local evidence. Pretrained analysis, StyleDNA-to-render orchestration,
> production desktop transport and the full offline Windows installer are not accepted.
> Start with [the recovery roadmap](docs/RECOVERY-ROADMAP.md),
> [audio job evidence](docs/RECOVERY-R2B2-REPORT.md) and
> [native-tool qualification](docs/NATIVE-MEDIA-PREP-REPORT.md) and
> [cut-candidate evidence/limits](docs/RECOVERY-R2B3-REPORT.md).

- Protocol: **v2.5.1** (`docs/PROTOCOL-v2.5.1.md`)
- Decisions & resolved contradictions: `docs/PROTOCOL-ISSUES.md`
- Progress ledger: `docs/PROGRESS-LEDGER.md`
- License inventory: `licenses/THIRD-PARTY.md`

## Architecture

```
frontend/    React 18 + Vite 7 + TypeScript 5 + Tailwind 3 (desktop UI)
backend/     FastAPI sidecar — SQLite, structlog, OSS adapters (loopback only)
src-tauri/   Tauri v2 shell — spawns the sidecar, hosts the webview
scripts/     build-installer.ps1 + pins.json (SHA-256 pinned artifacts)
docs/        protocol, decisions, ledgers, guides
```

The runtime target is offline: no telemetry, CDN or automatic downloads. Build-machine
provisioning is separate. Installed-app offline acceptance is still open; development checks
are not a certificate for the complete Windows product.

## Development (Linux/macOS sandbox or Windows)

Backend:
```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest --cov=app --cov-report=term-missing
ruff check . && ruff format --check .
python -m app            # serves http://127.0.0.1:8756
```

Frontend:
```bash
cd frontend
npm install
npm run lint && npm run test && npm run build
npm run dev              # http://localhost:1420 (proxies /api to the backend)
```

Desktop shell (Windows, needs Rust + WebView2):
```bash
cd src-tauri && cargo build --release
```

## Installer

```powershell
pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries  # light CI/smoke build ONLY
```
The full bundle remains blocked by model/WebView2 placeholder artifacts, native packaging and
runtime acceptance. FFmpeg now has a dated publisher-checksum pin. A light build omits pinned
binaries/models/fixed WebView2 and is not the promised full offline installer. Do not treat
`-UpdatePins` as licence/provenance review or manufacture hashes for placeholder URLs.

## Status

The historical ledger records 260/260 authored steps (100%), not 100% release readiness.
Recovery proceeds inspect → reuse OSS → integrate → test → collect evidence, without interim
approval stops under the Owner's latest instruction. Work stays on the session branch/PR #1;
only the Owner merges. Current acceptance and remaining blockers live in the linked reports.
