# Cutting Edge v2 — Install guide (v1.0.0, Windows)

> **Development/CI guide — release BLOCKED (2026-11-05).** The full installer is
> not approved or delivered. Model/runtime pins, genuine pretrained workflows and
> render/export acceptance are incomplete. See [DESKTOP-R2C-REPORT.md](DESKTOP-R2C-REPORT.md)
> and [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md). A green backend badge means local
> connectivity, not model availability or a successful edit/export.

The target is an offline-first sports editor. Application telemetry and automatic model
fetching are forbidden; complete installed/offline behavior still requires acceptance.

## 1. Build variants

| Build | Contents / status | Use |
|---|---|---|
| **Full delivery target — BLOCKED** | app + sidecar + approved LGPL FFmpeg + verified licensed models + fixed WebView2; ~3.5 GB is a budget, not a delivered size | Not available as an accepted release |
| **Light CI** | built UI + PyInstaller onedir sidecar and `_internal/`; uses machine WebView2 and PATH tools; no bundled pretrained models | Development/testing only; not a clean-machine offline or export certificate |

The installed resource home is resolved by the native shell, not the working directory.
`frontend/` is served by the sidecar on the same origin; Vite is only a development tool.
Do not separate the backend executable from its installed `_internal/` dependency tree.

## 2. Requirements

- Windows 10 21H2 or newer / Windows 11 (x64)
- 8 GB RAM minimum, 16 GB recommended for GPU export
- 6 GB free disk (full build) or 1 GB (light build)
- Optional NVIDIA GPU (GTX 1060 or newer) for the NVENC export target. OpenH264 is
  the approved fallback target; end-to-end export is not yet accepted.

## 3. Install

1. Download `CuttingEdgeV2-Setup-v1.0.0.exe` and `CuttingEdgeV2-Setup-v1.0.0.exe.sha256`.
2. Verify the hash (PowerShell):

   ```powershell
   Get-FileHash .\CuttingEdgeV2-Setup-v1.0.0.exe -Algorithm SHA256
   Get-Content .\CuttingEdgeV2-Setup-v1.0.0.exe.sha256
   ```

   The two values must match exactly.
3. Because the build is **not code-signed**, Windows shows "Windows protected your PC".
   Click **More info → Run anyway**. Details and the exact risk statement:
   `docs/bypass-smartscreen.md`.
4. Run the installer (per-machine). Pick the interface language (English / فارسی) when asked.
5. Launch **Cutting Edge v2** from the Start menu.

The first launch starts a local backend on `127.0.0.1:8756`. The status bar turns green
("processing core connected") when it answers; that call never leaves the machine.

## 4. Currently verified workflow

1. Import your authorized source/reference media. No third-party media ships in the bundle.
2. Preview supported source media (the source player is **not** a rendered timeline).
3. Place clips on the timeline, save the local project and reopen it.
4. Treat pretrained DNA/analysis, edited preview and final render as **unaccepted**, not
   successful because a wizard advances or a button changes state. Experimental native
   scene/audio measurements have separate local evidence and are default-disabled.

## 5. Where your data lives

| Path | Contents |
|---|---|
| `%APPDATA%\CuttingEdgeV2\cutting-edge.db` | projects, assets, jobs, artifacts |
| `%APPDATA%\CuttingEdgeV2\templates\` | your Style-Match templates |
| `%APPDATA%\CuttingEdgeV2\logs\backend.jsonl` | structured logs (support bundle) |
| Install folder `models/`, `binaries/ffmpeg/bin/` | bundled models and FFmpeg |

Reference videos, music, b-roll and voice-overs are **user-imported**; the installer never
ships third-party media.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Status bar stays red ("core unavailable") | sidecar blocked by antivirus | allow `cutting-edge-backend.exe`, restart the app |
| "FFmpeg not found" banner | light build without FFmpeg on `PATH` | install FFmpeg (LGPL build) and add `ffmpeg\bin` to `PATH`, or use the full build |
| Export/analysis unavailable | end-to-end renderer/models not yet accepted | do not treat a UI change as an exported file; inspect the release checklist |
| Import rejects a file | unsupported container | remux to MP4 (H.264/AAC) first |
| SmartScreen blocks every launch | unsigned binaries | `docs/bypass-smartscreen.md` |

Support bundle: *Help → Copy diagnostics* (or `GET http://127.0.0.1:8756/api/v1/system/diagnostics`)
plus the log file. Nothing is uploaded automatically.

## 7. Build it yourself

```powershell
pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries   # light build (CI)
```

Full builds require real reviewed artifact URLs, SHA-256, redistribution licenses and
fixed WebView2 inputs first. `-UpdatePins` is an operator tool, not a license audit or a
way to repair placeholder URLs. Current null/placeholder pins are not delivery-ready.

Prerequisites: Node 22, Python 3.11, Rust stable (MSVC toolchain), NSIS (installed by the
Tauri CLI on demand). Output: `delivery/CuttingEdgeV2-Setup-v1.0.0.exe` + `.sha256`.

## 8. Uninstall

*Settings → Apps → Cutting Edge v2 → Uninstall*. Your projects stay in `%APPDATA%\CuttingEdgeV2`.
The exact default-profile data-retention/uninstall behavior still needs target-machine
acceptance. Back up your data first; no automatic deletion option is certified here.
