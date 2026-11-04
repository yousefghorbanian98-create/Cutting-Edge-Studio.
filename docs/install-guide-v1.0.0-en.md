# Cutting Edge v2 — Install guide (v1.0.0, Windows)

Offline sports video editor for bodybuilding and volleyball creators. Nothing in this
application talks to the internet: no accounts, no telemetry, no model downloads.

## 1. What the installer contains

| Build | What is inside | When to use it |
|---|---|---|
| **Full (delivery)** | app + Python sidecar + FFmpeg (LGPL) + pose/CLIP/YOLOX/Whisper models + WebView2 fixed runtime | the normal install, fully offline, ~3.5 GB |
| **Light (CI)** | app + Python sidecar only; FFmpeg is resolved from `PATH`, models are optional | CI artifact, quick trial, or when you already ship FFmpeg |

Both builds install the same application; only the bundled media engine differs.

## 2. Requirements

- Windows 10 21H2 or newer / Windows 11 (x64)
- 8 GB RAM minimum, 16 GB recommended for GPU export
- 6 GB free disk (full build) or 1 GB (light build)
- Optional NVIDIA GPU (GTX 1060 or newer) for NVENC export; the app falls back to
  openh264 automatically and logs the fallback

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

## 4. First run

1. **Import** 10 bodybuilding clips (or volleyball footage) with the *Import* button.
2. **Pick a reference** — one video whose editing style you want to copy (see
   `docs/how-to-choose-references.md` for what makes a good reference).
3. Follow the five wizard steps: reference → DNA → analysis → compatibility → EDL.
4. Choose a platform preset in the **Post-production** panel, then *Build preview*.
5. Review the preview, then *Render final*.

## 5. Where your data lives

| Path | Contents |
|---|---|
| `%APPDATA%\CuttingEdgeV2\cutting-edge.db` | projects, assets, jobs, artifacts |
| `%APPDATA%\CuttingEdgeV2\templates\` | your Style-Match templates |
| `%APPDATA%\CuttingEdgeV2\logs\cutting-edge.log` | structured logs (support bundle) |
| Install folder `models/`, `binaries/ffmpeg/` | bundled models and FFmpeg |

Reference videos, music, b-roll and voice-overs are **user-imported**; the installer never
ships third-party media.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Status bar stays red ("core unavailable") | sidecar blocked by antivirus | allow `cutting-edge-backend.exe`, restart the app |
| "FFmpeg not found" banner | light build without FFmpeg on `PATH` | install FFmpeg (LGPL build) and add `ffmpeg\bin` to `PATH`, or use the full build |
| Export falls back to openh264 | no NVENC-capable GPU / driver | expected; CPU export is slower but lossless-compliant |
| Import rejects a file | unsupported container | remux to MP4 (H.264/AAC) first |
| SmartScreen blocks every launch | unsigned binaries | `docs/bypass-smartscreen.md` |

Support bundle: *Help → Copy diagnostics* (or `GET http://127.0.0.1:8756/api/v1/system/diagnostics`)
plus the log file. Nothing is uploaded automatically.

## 7. Build it yourself

```powershell
pwsh -File scripts/build-installer.ps1 -UpdatePins   # once, on a trusted network: fills SHA-256
pwsh -File scripts/build-installer.ps1               # full offline installer
pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries   # light build (CI)
```

Prerequisites: Node 22, Python 3.11, Rust stable (MSVC toolchain), NSIS (installed by the
Tauri CLI on demand). Output: `delivery/CuttingEdgeV2-Setup-v1.0.0.exe` + `.sha256`.

## 8. Uninstall

*Settings → Apps → Cutting Edge v2 → Uninstall*. Your projects stay in `%APPDATA%\CuttingEdgeV2`.
The uninstaller asks once: **"Also remove user data"** — it is **off by default**, and
ticking it deletes projects, templates and logs.
