# Release checklist — v1.0.0

> **2026-11-05:** release is **BLOCKED**. Local evidence and remaining integration gaps are in
> [LOCAL-TEST-REPORT.md](LOCAL-TEST-REPORT.md). Historical CI passes do not certify a delivered installer.

## A. Automated checks (local results and earlier CI evidence)

- [x] Backend: `ruff check .` + `ruff format --check .`
- [x] Backend: `pytest --cov=app` → 310 passed with provisioned optional/native analysis, coverage 93.66 %; base test mode 304 passed + 6 explicit optional skips (R2b4, not clean environment)
- [x] Backend: `pip-audit --strict` → no known advisories in the local Python environment after pytest 9.0.3 update (native libraries/Windows distribution not certified)
- [x] Frontend: `npm run lint`, `npm test` (168), `npm run build`
- [x] Frontend: `npm audit --audit-level=high` → 0 high/critical; 8 moderate dev-tool findings remain
- [x] Security baseline 3a1446a: official pinned MIT gitleaks 8.30.1 full-history scan passed PR 41914773884 and push 41914765825; redacted SARIF, failure status retained, no new allowlists. Earlier wrapper findings were not independently retrieved/reviewed.
- [x] R2b2 code/security revision 35281c1: PR 41925158413 PASS for backend/frontend/security, including the exact path + public digest exception negative controls and full-history scan. Earlier wrapper findings remain unreviewed. Later revisions require their own results.
- [x] Guardrails: `tests/test_hygiene.py` (offline, licences, E4)
- [x] Prior 3a1446a Windows NSIS light build: push 41914765825 SUCCESS and setup artifact metadata present. Uses WithoutPinnedBinaries; archive executable/SHA contents not independently retrieved. NOT full bundle, install/runtime/offline acceptance.

- [x] Native BtbN tool feasibility only: reviewed dated Windows LGPL shared archive, actual OpenH264 encode/probe/decode and native scdet one-cut assertions passed step in push 41926420920 on ffd3169; that encompassing run later cancelled; follow-up e62f847 push 41926876782 completed strict native probe AND NSIS light build ([report](NATIVE-MEDIA-PREP-REPORT.md)). Further follow-up 20dec09 push 41930777767 also completed strict native + light NSIS successfully; NOT full packaged app/worker, NVENC, quality or offline acceptance.

## A2. Integration acceptance (not cleared by unit tests)

- [x] Browser media import creates backend assets with usable local paths (R1 local evidence)
- [x] Source playback through registered asset IDs and HTTP ranges (not edit rendering)
- [x] Project/media/timeline saved workspace reopens after actual backend restart (R1b Linux/browser, 26 checks; [report](RECOVERY-R1B-REPORT.md))
- [x] R2a only: real-media full decode/hash/probe jobs, observed progress, cancellation, failure, restart/crash recovery and project isolation (26 local browser checks; [report](RECOVERY-R2A-REPORT.md)); diagnostic LGPL shared tools, not approved Windows runtime
- [x] R2b1 standalone OSS rhythm adapter: real librosa on 3 owned synthetic fixtures; not a project job/UI or real-music quality acceptance ([report](RECOVERY-R2B1-REPORT.md))
- [x] R2b2 experimental audio jobs/UI: 23/23 real local browser checks using owned clicks/silence/no-audio media; default-disabled, no real-music quality or Windows native acceptance ([report](RECOVERY-R2B2-REPORT.md))
- [x] R2b3 experimental native scdet candidate jobs/UI: 25/25 actual owned-stimulus browser checks, including original hashes, native 1/3-second candidates, no-video/static, cancel/error/stale/restart/interrupted/retry; default-disabled ([report](RECOVERY-R2B3-REPORT.md))
- [x] R2b4 conservative marked scratch recovery: 54/54 scene/audio browser checks; known inactive native/PCM crash workspaces recovered, live/unknown/legacy kept; local diagnostics/UI counts ([report](RECOVERY-R2B4-REPORT.md))
- [ ] Candidate adapter: independent native crash containment, unknown/legacy recovery policy, real sports/edit quality and actual Windows project/native packaging acceptance
- [ ] Audio: authorized real-music quality, video timestamp alignment, legacy/ambiguous PCM cache, native extraction-crash containment/resource hardening, audited optional/native Windows build
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
