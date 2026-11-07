# Compatibility matrix — v1.0.0

## Operating systems

| OS | Status | Notes |
|---|---|---|
| Windows 11 x64 (22H2+) | **supported** | fixed-version WebView2 is bundled, no OS update needed |
| Windows 10 x64 (21H2+) | **supported** | same; light build uses the machine's WebView2 (Evergreen) |
| Windows 10 x64 (< 21H2) | best effort | NSIS installer works, WebView2 runtime may need a manual install |
| Windows on ARM | not supported | NVENC and MediaPipe wheels are x64; no official build |
| Linux / macOS | **not shipped** | backend and frontend run in CI, the desktop shell is Windows-targeted |

## Hardware

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores, AVX2 | 8 cores / 16 threads (Ryzen 5 5600 / i5-12400 class) |
| RAM | 8 GB | 16 GB (Style Match peak measured under 4 GB in dev) |
| GPU | not required | NVIDIA GTX 1650+ (NVENC H.264, Turing better) |
| VRAM | 2 GB (CPU-only path) | 6 GB (CLIP + pose resident, one at a time) |
| Disk | 6 GB free (full build) | 20 GB free (projects + exports + proxies) |

Verified NVENC path: driver ≥ 470 on GTX 1650. CUDA is **not** required (onnxruntime CPU
default, GPU optional through provider selection).

## Codecs

| Container | Import | Export |
|---|---|---|
| MP4 (H.264 / HEVC) | yes | H.264 (NVENC or openh264) |
| MOV (ProRes / H.264) | yes | — |
| MKV | yes | — |
| WebM (VP9) | decode only | — |
| AV1 | decode only (if FFmpeg build supports it) | — |

Audio export: AAC 192 kbit/s. Loudness targets: TikTok/YouTube −14 LUFS, broadcast −23 LUFS.

## Runtime dependencies shipped to the user

| Item | Version policy |
|---|---|
| Python sidecar | CPython 3.11, frozen by PyInstaller 6.22.3 |
| FFmpeg | BtbN **LGPL shared** build, pinned by SHA-256 (`scripts/pins.json`) |
| WebView2 | Fixed-Version Runtime (full build) / machine runtime (light build) |
| Models | MediaPipe pose (bundled wheel), CLIP ViT-B/32, YOLOX-s, faster-whisper base, TransNetV2; all ≤ 3 GB, no auto-download |

## Languages

| Locale | UI | Captions | Notes |
|---|---|---|---|
| فارسی (`fa`) | full, RTL | ASS with RTL override marks | default language |
| English (`en`) | full, LTR | SRT/ASS | |

## Not supported on purpose

- Any network feature (accounts, cloud render, telemetry, model downloads).
- GPL codecs: `libx264`/`libx265` are never linked or invoked.
- GPU vendors other than NVIDIA for hardware encode (AMF/QSV are not wired in v1.0.0).
