# R6 — Release Acceptance (lightweight)

Date: 2026-11-05 · Branch `arena/dbb53bc2-cutting-edge-studio` · Status IN PROGRESS lightweight

## Gate

Clean Windows install/uninstall; genuine model quality; NVENC/openh264 performance; fully offline run.

## Lightweight verdict (CI-tractable)

- VERSION `1.0.0` consistent across `VERSION`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml` — verified by `test_release_guardrails.py::test_version_consistent_across_manifests`.
- Changelog `[1.0.0]` + Known issues (unsigned/SmartScreen) + `docs/RELEASE-NOTES-v1.0.0.md` present and mentions offline.
- Full offline bundle honestly blocked: `docs/RELEASE-CHECKLIST.md` still has unchecked `[ ] pins.json non-null hashes` and `[ ] Full packaged Tauri/approved fixed runtime` — no false success claim.
- Rust shell has no runtime downloads: no `reqwest`, sidecar on `127.0.0.1`, `CUTTING_EDGE_HOME` only — verified by `test_release_guardrails.py::test_rust_offline_no_runtime_downloads`.
- CI light installer remains green (WithoutPinnedBinaries) — real build without bundling unpinned models, as intended for lightweight phase.

## Not claimed in lightweight

- Real Windows clean-machine install/uninstall cycle (needs isolated Windows host, manual).
- Genuine model quality under real media (needs pinned model bundle and NVENC hardware).
- Throughput/latency numbers for NVENC vs openh264 (needs Windows hardware).
- Full 3.5 GB offline bundle with fixed WebView2 runtime (needs `-UpdatePins` on trusted network and `-full` build, currently BLOCKED by design).

## Heavy (post-lightweight, when trusted Windows + models available)

1. `pwsh -File scripts/build-installer.ps1 -UpdatePins` → review `git diff scripts/pins.json`
2. `pwsh -File scripts/build-installer.ps1` (full, ~3.5 GB) → publish `.exe` + `.sha256`
3. Manual B1–B12 from `docs/RELEASE-CHECKLIST.md` on clean Windows 11, offline repeat.
4. Attach evidence artifacts and push tag `v1.0.0`.

## References

- `backend/tests/test_release_guardrails.py` — 4 guardrail tests
- `docs/RELEASE-CHECKLIST.md` — authoritative checklist (honest BLOCKED state)
- `docs/RELEASE-NOTES-v1.0.0.md` / `CHANGELOG.md` — user-facing release truth
