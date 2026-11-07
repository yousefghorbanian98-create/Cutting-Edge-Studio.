# Pre-1.0 Release Checklist — no gaps (professor §6)

All items must be ☐→☑ with evidence before tagging `v1.0.0`.

| # | Gate | Evidence file | How to verify |
|---|------|---------------|---------------|
| B1 | `pins.json` has **0 null** sha256 | `scripts/pins.json` + `scripts/verify_pins.py --strict` exit 0 | `python scripts/verify_pins.py --strict` |
| B2 | VM dry-run **B1-B12** Light→Full on clean Win11 | `delivery/verification-logs/installer-test.txt` | Run `Setup.ps1 -Silent` on VM |
| B3 | VM **C2** offline — no network leak (TCP dump) | `delivery/verification-logs/offline-tcpdump.log` | `Get-NetTCPConnection` during render |
| B4 | Piper binary + voice hash pinned + license audit | `scripts/pins.json` + `licenses/PIPER.md` | `pip-licenses` + VMAF |
| B5 | openh264 **not** bundled (Cisco plugin download only) | `git ls-files \| grep openh264` empty | Check bundle |
| B6 | Token guard: `curl without x-ces-token → 401` | `backend/tests/test_security_guard.py::test_401_without_token` green | `curl http://127.0.0.1:8756/api/v1/health -i` |
| B7 | Host/Origin guard: evil Host/Origin → 403 | `test_403_bad_*` green | `curl -H "Host: evil.com" ...` |
| B8 | Random port: `--port 0` assigns free port + receipt | `test_desktop_listener_random_port` green + `PORT=...` stdout | `python -m app --port 0 --serve-frontend` |
| B9 | NSIS installer **signed** (SignPath) | `delivery/CuttingEdgeV2-Setup-v1.0.0.exe` Authenticode | `Get-AuthenticodeSignature` |
| B10 | SBOM + CVE: `syft` + `osv-scanner` + `pip-audit` + `cargo audit` | `delivery/sbom.spdx.json` + CI logs | `gh run view` |
| B11 | Quality metrics: ASL/Wasserstein/ΔE/beat F1 + 5-user study | `docs/BENCHMARK-QUALITY.yaml` + `reports/quality.json` | `pytest -k quality` |
| B12 | a11y: Playwright + axe-core (0 critical) | `ci-windows.yml` windows-smoke job green | `npx axe` |

## Commands to generate evidence (local)

```powershell
# 1. Pins
python scripts/verify_pins.py --strict  # must exit 0

# 2. Security (loop S1)
$env:CES_API_TOKEN="test"
python -m pytest backend/tests/test_security_guard.py -v
curl.exe -H "x-ces-token: wrong" http://127.0.0.1:8756/api/v1/health # -> 401

# 3. Quality
python -m pytest backend/tests/test_stylematch_quality.py -v

# 4. SBOM & licenses
syft packages dir:. -o spdx-json=delivery/sbom.spdx.json
pip-licenses --format=json --output-file delivery/licenses.json
osv-scanner --recursive .

# 5. Windows build (on Win11 VM)
pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries
```

## Loop mapping (inspect→reuse→integrate→test→evidence→ledger)

Each B-item is a loop iteration — see `docs/RECOVERY-ROADMAP.md` R7-R12.
