# Release checklist — v1.0.0

> **2026-11-05:** release is **BLOCKED**. Local evidence and remaining integration gaps are in
> [LOCAL-TEST-REPORT.md](LOCAL-TEST-REPORT.md). Historical CI passes do not certify a delivered installer.

## A. Automated checks (local results and earlier CI evidence)

- [x] Backend: `ruff check .` + `ruff format --check .`
- [x] Backend: `pytest --cov=app` → 256 passed with optional analysis, coverage 93.80 %; base test mode 253 passed + 3 explicit optional skips
- [x] Backend: `pip-audit --strict` → no known advisories in the local Python environment after pytest 9.0.3 update (native libraries/Windows distribution not certified)
- [x] Frontend: `npm run lint`, `npm test` (161), `npm run build`
- [x] Frontend: `npm audit --audit-level=high` → 0 high/critical; 8 moderate dev-tool findings remain
- [x] Security baseline 3a1446a: official pinned MIT gitleaks 8.30.1 full-history scan passed PR 41914773884 and push 41914765825; redacted SARIF, failure status retained, no new allowlists. Earlier wrapper findings were not independently retrieved/reviewed.
- [ ] Current R2b2 revision CI: pending at report authoring; prior baseline CI does not clear a new revision.
- [x] Guardrails: `tests/test_hygiene.py` (offline, licences, E4)
- [x] Prior 3a1446a Windows NSIS light build: push 41914765825 SUCCESS and setup artifact metadata present. Uses WithoutPinnedBinaries; archive executable/SHA contents not independently retrieved. NOT full bundle, install/runtime/offline acceptance.

## A2. Integration acceptance (not cleared by unit tests)

- [x] Browser media import creates backend assets with usable local paths (R1 local evidence)
- [x] Source playback through registered asset IDs and HTTP ranges (not edit rendering)
- [x] Project/media/timeline saved workspace reopens after actual backend restart (R1b Linux/browser, 26 checks; [report](RECOVERY-R1B-REPORT.md))
- [x] R2a only: real-media full decode/hash/probe jobs, observed progress, cancellation, failure, restart/crash recovery and project isolation (26 local browser checks; [report](RECOVERY-R2A-REPORT.md)); diagnostic LGPL shared tools, not approved Windows runtime
- [x] R2b1 standalone OSS rhythm adapter: real librosa on 3 owned synthetic fixtures; not a project job/UI or real-music quality acceptance ([report](RECOVERY-R2B1-REPORT.md))
- [x] R2b2 experimental audio jobs/UI: 23/23 real local browser checks using owned clicks/silence/no-audio media; default-disabled, no real-music quality or Windows native acceptance ([report](RECOVERY-R2B2-REPORT.md))
- [ ] Audio: authorized real-music quality, video timestamp alignment, orphan PCM cache/extraction-crash/resource hardening, audited optional/native Windows build
- [ ] Wizard starts genuine pretrained model analysis and shows backend progress/results
- [ ] Preview/export controls invoke the approved renderer and play the result
- [ ] Packaged Tauri has working sidecar API routing without Vite
- [ ] Real model/beat/shot/color measurements replace synthetic analysis fixtures
- [ ] NVENC or openh264 export passes using the approved LGPL shared build

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
