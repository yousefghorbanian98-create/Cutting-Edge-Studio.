# Release checklist — v1.0.0

## A. Automated (green in CI on this branch)

- [x] Backend: `ruff check .` + `ruff format --check .`
- [x] Backend: `pytest --cov=app` → 117 passed, coverage 94.10 %
- [x] Backend: `pip-audit -r requirements.txt --strict` → no known vulnerabilities
- [x] Frontend: `npm run lint`, `npm test` (108), `npm run build`
- [x] Frontend: `npm audit --audit-level=high` → 0 high/critical
- [x] Security: gitleaks + trivy (CRITICAL)
- [x] Guardrails: `tests/test_hygiene.py` (offline, licences, E4)
- [x] Installer: Windows NSIS build produces `CuttingEdgeV2-Setup-v1.0.0.exe` + `.sha256`

## B. Owner-machine acceptance (fill in, do not pre-check)

| # | Check | Command / action | Result |
|---|---|---|---|
| B1 | Install on clean Windows 11 | run setup, launch | ☐ |
| B2 | Status bar green | observe | ☐ |
| B3 | Import 10 clips + 1 reference | Media panel | ☐ |
| B4 | Style Match end-to-end | wizard steps 1-5 | ☐ |
| B5 | Golden Set ≥ 3 of 5 metrics | `POST /stylematch/score` | ☐ |
| B6 | 200-clip timeline ≥ 30 fps | DevTools trace | ☐ |
| B7 | 60 s NVENC export ≤ 60 s | stopwatch | ☐ |
| B8 | openh264 fallback export ≤ 240 s | GPU off | ☐ |
| B9 | Peak RAM < 4 GB | Task Manager | ☐ |
| B10 | Uninstall keeps `%APPDATA%` | uninstall/reinstall | ☐ |
| B11 | "Also remove user data" deletes it | uninstall | ☐ |
| B12 | Offline run (adapter unplugged) | repeat B4 | ☐ |

## C. Full offline build (one-time, trusted network)

```powershell
pwsh -File scripts/build-installer.ps1 -UpdatePins   # writes real SHA-256 values
git diff scripts/pins.json                           # review every hash
pwsh -File scripts/build-installer.ps1               # full installer, ~3.5 GB
```

- [ ] `scripts/pins.json` has non-null hashes for FFmpeg + every model
- [ ] WebView2 fixed runtime placed in `src-tauri/webview2-fixed-runtime/`
- [ ] Installer size within the 3.5 GB budget
- [ ] `delivery/CuttingEdgeV2-Setup-v1.0.0.exe.sha256` published next to the binary

## D. Publication

- [ ] Tag `v1.0.0` on the merged commit
- [ ] Attach `CuttingEdgeV2-Setup-v1.0.0.exe`, `.sha256`, `docs/RELEASE-NOTES-v1.0.0.md`
- [ ] Note in the release body: unsigned build → SmartScreen instructions link
