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
| fastapi | 0.162.0 | MIT | HTTP layer of the sidecar |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server (loopback only) |
| pydantic / pydantic-settings | 2.14.2 / 2.16.2 | MIT | Schemas + settings |
| SQLAlchemy | 2.1.8 | MIT | Local SQLite ORM |
| structlog | 26.1.0 | MIT / Apache-2.0 (dual) | Structured local logging |
| httpx | 0.28.1 | BSD-3-Clause | Test client transport |
| psutil | 7.2.2 | BSD-3-Clause | Local process/resource probes |
| numpy | 2.1.3 | BSD-3-Clause | Numerics |
| scipy | 1.14.1 | BSD-3-Clause | Signal processing (peaks, KS-test, filtering) |
| sqlite (bundled with CPython) | 3.x | Public domain | Project database |
| React / React DOM | 18.3.1 | MIT | UI runtime |
| starlette | 1.10.0 | BSD-3-Clause | ASGI toolkit (FastAPI core) |
| python-multipart | 0.0.33 | Apache-2.0 | Multipart parsing for asset upload |
| Vite | 7.3.7 | MIT | Dev server + bundler |
| TypeScript | 5.7.2 | Apache-2.0 | Type system |
| Tailwind CSS | 3.4.17 | MIT | Styling |
| zustand | 4.5.5 | MIT | UI state |
| zod | 4.6.7 | MIT | Versioned workspace validation (R1b); notice in `ZOD-MIT.md` |
| clsx | 2.1.1 | MIT | Class composition |
| tailwind-merge | 2.6.0 | MIT | Class conflict resolution |
| lucide-react | 0.469.0 | ISC | Icons |
| Vitest / jsdom | 2.1.8 / 25.0.1 | MIT | Frontend tests |
| @testing-library/* | 16.1.0 / 6.6.3 | MIT | Component tests |
| ESLint (+ typescript-eslint) | 8.57.1 / 8.19.1 | MIT | Lint |
| ruff | 0.8.4 | MIT | Python lint/format |
| pytest / pytest-cov | 9.0.3 / 6.0.0 | MIT | Backend tests |
| PyInstaller | 6.22.3 | GPLv2+ **with bootloader exception** | Sidecar packaging |
| @radix-ui/react-* (dialog, select, tabs, switch, slider, progress, tooltip, dropdown-menu, checkbox, separator, scroll-area) | 1.x / 2.x | MIT | Accessible primitives (P1) |
| framer-motion | 11.15.0 | MIT | Wizard step transitions |
| sonner | 1.7.1 | MIT | Toasts |
| cmdk | 1.0.4 | MIT | Command palette |
| @dnd-kit/core · sortable · utilities | 6.3.1 · 10.0.0 · 3.2.2 | MIT | Media list reordering |
| @fontsource/vazirmatn · inter · jetbrains-mono | 5.1.1 | OFL-1.1 | Bundled fonts (no CDN) |
| axe-core | 4.10.2 | MPL-2.0 | Accessibility test runner (dev only) |
| @xzdarcy/react-timeline-editor | 1.0.0 | MIT | Timeline MVP (successor of the unpublished `react-timeline-editor`) |
| @xzdarcy/timeline-engine | 1.x | ISC | Timeline engine behind the editor |
| react-virtualized | 9.x | MIT | Row/scroll virtualization for the timeline |
| react-hotkeys-hook | 4.6.1 | MIT | Keyboard shortcuts |
| immer | 10.1.1 | MIT | Immutable timeline edits |
| Tauri | 2.x | MIT / Apache-2.0 | Desktop shell |
| tauri-plugin-shell | 2.6.0 | MIT / Apache-2.0 | Sidecar spawning |

## Planned third-party runtime (declared, not yet wired)

| Component | License | Notes |
|---|---|---|
| FFmpeg (BtbN **LGPL shared** build) | LGPL-2.1+ (dynamic) | `libx264` is GPL → never shipped. H.264 via NVENC, fallback openh264 (BSD-2). |
| MediaPipe | Apache-2.0 | Task adapter requires a separately verified local `.task` artifact; do not assume the wheel supplies the required weights. |
| YOLOX-s | Apache-2.0 code / MIT weights | Replaces YOLO-NAS (LOCK-04 v2.5.1) |
| CLIP ViT-B/32 (ONNX) | MIT | Zero-shot shot/action classification |
| faster-whisper (base) | MIT | ASR for captions; weights pinned by SHA-256 |
| Piper TTS + voices | MIT code / per-voice | Each voice license audited before bundling |
| TransNet V2 | MIT | Shot boundary detection |
| librosa 0.11.0 | ISC | Experimental rhythm adapter and isolated project-job/UI glue tested in R2b1/R2b2; default-disabled, not default runtime. Notice in `LIBROSA-ISC.md`; native/transitive/Windows packaging review remains open. |
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

## P3-P9 additions (code we wrote, libraries we call)

| Component | Version | License | Usage |
|---|---|---|---|
| FFmpeg (BtbN, LGPL shared build) | pinned in `scripts/pins.json` | LGPL-2.1-or-later (dynamic link only) | probe / decode / encode / mux |
| openh264 (Cisco) | shipped by FFmpeg `libopenh264` | BSD-2-Clause | H.264 software fallback |
| MediaPipe (Python) | bundled in wheel | Apache-2.0 | 33-point pose landmarks on CPU |
| Ultralytics-free detector: YOLOX-s | weights ~35 MB | Apache-2.0 code / MIT weights | person/object boxes (no auto-download) |
| CLIP ViT-B/32 ONNX | 150 MB | MIT | zero-shot shot types, b-roll ranking |
| faster-whisper (base) | 145 MB | MIT | captions |
| TransNetV2 ONNX | 12 MB | MIT | shot boundary detection |
| Real-ESRGAN (optional) | 64 MB | BSD-3-Clause | upscaling, off by default |
| librosa + scipy.signal | 0.10.x / 1.14.1 | ISC / BSD-3-Clause | beat grid and peak picking |
| PyInstaller | 6.22.3 | GPLv2-or-later **with bootloader exception** | sidecar packaging (explicitly whitelisted) |
| WebView2 Fixed-Version Runtime | Microsoft | proprietary redistribution, allowed | the UI engine, bundled offline |
| @xzdarcy/react-timeline-editor | 1.0.0 | MIT (fork of `react-timeline-editor`) | timeline surface |
| Konva / react-konva | 9.x | MIT | canvas overlays (RTL text via `direction: 'rtl'`) |
| framer-motion | 12.x | MIT | UI transitions |
| lucide-react | 0.4xx | ISC | icon set |

### Dev-only tooling (never shipped in the installer)

| Component | Version | License |
|---|---|---|
| pytest / pytest-cov / pytest-asyncio | 8.3.4 / 6.0.0 / 0.25.0 | MIT / Apache-2.0 |
| ruff | 0.8.4 | MIT |
| mypy | 1.14.0 | MIT |
| pip-audit | 2.7.3 | Apache-2.0 |
| vitest | 3.2.7 | MIT |
| eslint + typescript-eslint | 9.x / 8.x | MIT |
| @vitejs/plugin-react | 5.2.0 | MIT |

### Deliberate exclusions (re-verified in P8)

`libx264`/`libx265` (GPL, never linked) · `ultralytics`/YOLOv8 (AGPL) · YOLO-NAS weights
(non-commercial) · `madmom` (dead upstream + CC-BY-NC-SA models) · Ollama / InternVL /
VideoLLaMA3 (no redistribution rights, offline policy) · RobustVideoMatting, HotClip, Concat
(GPL) · any telemetry SDK.

### R2b1 optional-analysis qualification

`librosa.beat.beat_track` was tested directly rather than writing a new detector. The optional
analysis dependency selection is exploratory, not an approved shipping lock. Default backend
requirements do not include librosa. Python-SoXR 1.1.0 was source-built against an external
shared libsoxr for these tests; the default prebuilt wheel was not assumed to meet the project's
dynamic-only LGPL policy. No test native binaries/source archives are bundled. Audit each
transitive licence, native component and Windows artifact before enabling distribution.
See `docs/RECOVERY-R2B1-REPORT.md` and its linkage/provenance evidence.

### R2b2 reuse and remaining distribution gate

Existing FFmpeg PCM conversion, librosa beat tracking, psutil process identity/liveness,
JobRegistry/Artifact/runner, FastAPI/Pydantic and the existing React/Radix/Zod panel are reused.
No custom detector, training, imported n8n workflow or new scheduler is claimed.
Alternatives and the exact integration boundary are recorded in `docs/RECOVERY-R2B2-REPORT.md`.
No dependency was added to default requirements. The explicit experimental flag defaults false.
Linux source-built diagnostic FFmpeg/SoXR and local browser checks do not certify Windows
linkage/licences, packaged worker startup, model inference, musical quality or distribution.
