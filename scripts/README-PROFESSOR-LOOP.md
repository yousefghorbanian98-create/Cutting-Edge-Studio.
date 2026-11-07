# Professor feedback → reusable loop (inspect → reuse OSS → integrate → test → evidence → ledger)

Each of the 6 items is a loop iteration — not a one-off patch.

| Iter | Professor item | Inspect | Reuse OSS | Integrate | Test | Evidence | Ledger |
|------|----------------|---------|-----------|-----------|------|----------|--------|
| R7 | Token+Host/Origin+random port | Tauri shell only localhost, no token | `hmac`, `secrets`, `SecurityMiddleware` | `backend/app/security.py` + `main.py` + `__main__.py:port0` + Rust `generate_token` | `test_security_guard.py` (401/403/200 + port0) | CI green + `curl -H x-ces-token` 401 | RECOVERY-ROADMAP R7 |
| R8 | verify_pins fail-closed | 6 null hashes block Full | `hashlib.sha256` | `scripts/verify_pins.py` strict + `build-installer --strict` | `test_packaging_guardrails` + `verify_pins --strict` fails on null | `delivery/verification-logs/pins.txt` | R8 |
| R9 | StyleMatch metrics | No objective measure | `numpy/scipy/librosa`, `PySceneDetect` | `docs/BENCHMARK-QUALITY.yaml` + `test_stylematch_quality.py` | ASL 0.25s, W 0.18, ΔE 2.3, beat F1 0.65; 5-user Likert ≥3.5 | `reports/quality.json` bounded <4k | R9 |
| R10 | CI Windows hardening | `ci.yml` only Linux | `zizmor`, `pip-audit`, `cargo-audit`, `Playwright`, `axe-core` | `.github/workflows/ci-windows.yml` SHA-pinned + steps | `ci-windows.yml` lint/audit/build/SBOM | GH Actions green | R10 |
| R11 | OSS tooling: sbom/osv/sign/vmaf/structlog/updater | No provenance | `syft`, `osv-scanner`, `SignPath`, `pip-licenses`, `VMAF`, `structlog`, `tauri-plugin-updater` | `scripts/build-installer.ps1` SBOM step + `pyproject.toml` deps | `pip-licenses.json` + `sbom.spdx.json` artifacts | delivery SBOM | R11 |
| R12 | Pre-1.0 checklist | Checklist loose | `NSIS signed`, `Win11 VM` | `docs/RELEASE-CHECKLIST-1.0.md` B1-B12 | `verify_pins --strict` + VM B1-B12/C2 + token curl 401 | VM logs + signed exe | R12 |

Single installer runs all stages: `OneClick-Setup.ps1` shows 6 circles (Prereqs→Verify→Location→Pins→Build→Final) and each circle internally checks R7-R12 with colored lines.

Raw ultimate: `https://raw.githubusercontent.com/yousefghorbanian98-create/Cutting-Edge-Studio./arena/184ede4b-cutting-edge-studio/docs/AI-CONTEXT-RAW.md`
