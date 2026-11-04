# Evidence Report — approved-tool pin and Windows native probe preparation

2026-11-05 · same branch / PR #1, Owner merges. **Preparation, not runtime acceptance.**
Historical authored steps remain **260/260 (100%)**, NOT full release readiness.

## Why this step

R2b2 audio jobs/UI passed locally, and post-correction PR CI **41925158413** on
`35281c1` passed backend, frontend and security. The real pinned gitleaks CLI passed
both the exact public-checksum exception boundary test and the full repository history scan.
The corresponding push run is separate; Windows light-build completion is not assumed.

The next analysis adapters require trustworthy native tooling/artifacts. Inspection found:

- `scripts/pins.json` still had a floating FFmpeg URL and no archive checksum.
- Official TransNetV2 inference documentation requires TensorFlow and Git-LFS weights;
  the inspected repository files are LFS pointers, not usable weights. There is no verified
  local ONNX model/adapter yet. Do not load a pointer or a random mirror and claim inference.
- A ready-library alternative for shot candidates is FFmpeg's LGPL `scdet`, already available
  in full FFmpeg builds. It is not TransNetV2 or semantic scene understanding. A native synthetic
  one-cut feasibility test is added before considering project/API/UI integration.
- PySceneDetect adds OpenCV/PyAV/native provisioning and licence review; that is avoidable for
  an initial candidate-measurement experiment. No new scene detector or custom ML is written.

## Pinned publisher artifact

Selected **BtbN Windows x64 LGPL shared, 9.0 release branch**, dated monthly build
`autobuild-2026-10-31-12-59`, asset `ffmpeg-n9.0.2-39-g7adfbe40dc-win64-lgpl-shared-9.0.zip`.
A monthly retained tag avoids the daily build's 14-day retention and the changing `latest` URL;
upstream retention policy is not an absolute availability guarantee.

Archive SHA-256: `e907b01fa4783913151237e37df2a10fa97d99a1598a021bf59d4ae62ffed4c0`.
The digest and URL were independently read from the publisher release asset metadata, not
invented or computed from an unidentified local binary. [Recorded metadata](evidence/native-media/publisher-metadata.json).
No build-time model or WebView2 placeholder pins are silently filled.

Sources inspected:
- `https://github.com/BtbN/FFmpeg-Builds/blob/master/README.md`: variants and retention.
- `https://github.com/BtbN/FFmpeg-Builds/blob/master/scripts.d/50-openh264.sh`: BSD OpenH264 build integration.
- `https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/autobuild-2026-10-31-12-59`: asset/digest provenance.
- `https://github.com/soCzech/TransNetV2/blob/master/inference/README.md`: actual dependencies and LFS weights.

## Authored probe, not yet an observed result

The existing Windows CI job now checks out the **triggering commit**, not a potentially moved
branch tip, and runs `scripts/ci/windows-native-media.ps1` before installer compilation.
Downloads happen on the **build machine only**, never in the application. The sandbox's blocked
release-asset redirect is not bypassed through a proxy or random mirror.

The probe must:

1. Download that exact archive into a new runner temporary directory and verify its SHA-256.
2. Run the actual Windows executables and check shared/non-GPL/nonfree configuration,
   LGPL licence output, shared avcodec DLL presence and absence of forbidden GPL encoders.
3. Require `libopenh264`; do not substitute libx264 or invent an available fallback.
4. Encode an owned one-second 160×96 black H.264 fixture using real OpenH264, verify actual
   ffprobe codec/dimensions/duration, then error-check a real decode.
5. If `scdet` is present, use ffprobe's JSON output on an owned black→white filter-source clip
   and verify exactly one native detector candidate at one second. No hand-written detector/parser.
6. Upload only JSON evidence (configuration/licence/encoders/probe facts), not media or binaries.

**Windows native execution is pending.** A pin and script are not evidence that these checks passed.
The separate full installer still has unfilled model/WebView2 pins, resource layout/routing work,
optional/native licence review and clean-install/offline/GUI acceptance gates. This probe cannot
clear those gates, certify every transitive native component, establish NVENC performance or
replace the application's unimplemented renderer/model orchestration.
