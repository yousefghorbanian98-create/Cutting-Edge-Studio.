# Cutting Edge v2

Offline-first sports video editor (bodybuilding + volleyball) for Windows.
Core feature: **Style Match** — analyse a reference edit's DNA and apply it to your own clips.

- Protocol: **v2.5.1** (`docs/PROTOCOL-v2.5.1.md`)
- Decisions & resolved contradictions: `docs/PROTOCOL-ISSUES.md`
- Progress ledger: `docs/PROGRESS-LEDGER.md`
- License inventory: `licenses/THIRD-PARTY.md`

## Architecture

```
frontend/    React 18 + Vite 5 + TypeScript 5 + Tailwind 3 (desktop UI)
backend/     FastAPI sidecar — SQLite, structlog, OSS adapters (loopback only)
src-tauri/   Tauri v2 shell — spawns the sidecar, hosts the webview
scripts/     build-installer.ps1 + pins.json (SHA-256 pinned artifacts)
docs/        protocol, decisions, ledgers, guides
```

Runtime is fully offline: no telemetry, no auto-update, no CDN, no runtime downloads.

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
pwsh -File scripts/build-installer.ps1 -UpdatePins   # once, trusted network
pwsh -File scripts/build-installer.ps1               # produces delivery/*.exe + .sha256
```
The script refuses to build while any artifact hash in `scripts/pins.json` is `null`.

## Status

P0 delivered (20/260 steps). Phase-by-phase delivery: each phase ends with an evidence report
and requires Owner approval before the next phase starts.
