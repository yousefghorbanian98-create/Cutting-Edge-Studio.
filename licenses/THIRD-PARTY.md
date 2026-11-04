# Third-Party Licenses — Cutting Edge v2 (protocol v2.5.1)

Whitelist: MIT · BSD 2/3/0 · Apache-2.0 · ISC · zlib · MPL-2.0 · LGPL (dynamic only) ·
Unicode · Unlicense · CC0 · PSF · OFL-1.1 · Boost · PyInstaller-Bootloader-Exception.

Blacklist (never linked, never bundled): GPL (standalone) · AGPL · CC-BY-NC ·
CC-BY-SA (as code) · SSPL · BUSL · proprietary · non-commercial weights.

> Rule: the **weights** license is audited separately from the code license.
> `yolo-nas` (non-commercial weights) and `madmom` (CC-BY-NC-SA models) were removed for
> this reason — see `docs/PROTOCOL-ISSUES.md` C1/C2.

## Runtime dependencies (implemented in this repository)

| Component | Version | License | Usage |
|---|---|---|---|
| fastapi | 0.115.6 | MIT | HTTP layer of the sidecar |
| uvicorn | 0.34.0 | BSD-3-Clause | ASGI server (loopback only) |
| pydantic / pydantic-settings | 2.10.4 / 2.7.0 | MIT | Schemas + settings |
| SQLAlchemy | 2.0.36 | MIT | Local SQLite ORM |
| structlog | 24.4.0 | MIT / Apache-2.0 (dual) | Structured local logging |
| httpx | 0.28.1 | BSD-3-Clause | Test client transport |
| psutil | 6.1.1 | BSD-3-Clause | Local process/resource probes |
| numpy | 2.1.3 | BSD-3-Clause | Numerics |
| scipy | 1.14.1 | BSD-3-Clause | Signal processing (peaks, KS-test, filtering) |
| sqlite (bundled with CPython) | 3.x | Public domain | Project database |
| React / React DOM | 18.3.1 | MIT | UI runtime |
| Vite | 5.4.21 | MIT | Dev server + bundler |
| TypeScript | 5.7.2 | Apache-2.0 | Type system |
| Tailwind CSS | 3.4.17 | MIT | Styling |
| zustand | 4.5.5 | MIT | UI state |
| clsx | 2.1.1 | MIT | Class composition |
| tailwind-merge | 2.6.0 | MIT | Class conflict resolution |
| lucide-react | 0.469.0 | ISC | Icons |
| Vitest / jsdom | 2.1.8 / 25.0.1 | MIT | Frontend tests |
| @testing-library/* | 16.1.0 / 6.6.3 | MIT | Component tests |
| ESLint (+ typescript-eslint) | 8.57.1 / 8.19.1 | MIT | Lint |
| ruff | 0.8.4 | MIT | Python lint/format |
| pytest / pytest-cov | 8.3.4 / 6.0.0 | MIT | Backend tests |
| PyInstaller | 6.22.3 | GPLv2+ **with bootloader exception** | Sidecar packaging |
| Tauri | 2.x | MIT / Apache-2.0 | Desktop shell |
| tauri-plugin-shell | 2.x | MIT / Apache-2.0 | Sidecar spawning |

## Planned third-party runtime (declared, not yet wired)

| Component | License | Notes |
|---|---|---|
| FFmpeg (BtbN **LGPL shared** build) | LGPL-2.1+ (dynamic) | `libx264` is GPL → never shipped. H.264 via NVENC, fallback openh264 (BSD-2). |
| MediaPipe | Apache-2.0 | Pose/face/hands/segmentation; models ship inside the wheel |
| YOLOX-s | Apache-2.0 code / MIT weights | Replaces YOLO-NAS (LOCK-04 v2.5.1) |
| CLIP ViT-B/32 (ONNX) | MIT | Zero-shot shot/action classification |
| faster-whisper (base) | MIT | ASR for captions; weights pinned by SHA-256 |
| Piper TTS + voices | MIT code / per-voice | Each voice license audited before bundling |
| TransNet V2 | MIT | Shot boundary detection |
| librosa | ISC | Beat/onset/tempo (replaces madmom) |
| color-matcher | BSD-3-Clause | Color transfer |
| OpenCV | Apache-2.0 | Optical flow, HoughLines, Laplacian |
| Konva.js | MIT | Telestration canvas |
| wavesurfer.js | BSD-3-Clause | Audio waveform |
| react-timeline-editor | MIT | MVP timeline (100–200 clips) |
| Vazirmatn / Inter / JetBrains Mono | OFL-1.1 | Bundled fonts |
| python-embed 3.11 | PSF-2.0 | Embedded interpreter |
| WebView2 Fixed-Version Runtime | Microsoft EULA (redistributable) | Offline webview |

## Deliberately excluded

| Component | Reason |
|---|---|
| YOLO-NAS (super-gradients) | Weights are non-commercial and non-redistributable |
| YOLOv8 / Ultralytics | AGPL-3.0 |
| madmom | No cp311 wheels; pretrained models are CC-BY-NC-SA |
| Ollama | Blocked in target region; also violates LOCK-05 |
| libx264 | GPL |
| CUDA / cuDNN DLLs | Proprietary redistribution + 1.5GB budget |
| Bundled reference videos / music | Third-party copyright |
