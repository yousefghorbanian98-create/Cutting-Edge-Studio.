# C1 — Benchmark Contract (lightweight)

Date: 2026-11-05 · Branch `arena/dbb53bc2-cutting-edge-studio` · Status SPECIFIED (observations UNKNOWN)

This contract fixes the competitor comparison inputs/tasks before observing products.
No competitor artifact/version is currently supplied or installed.

## Targets

- CapCut Desktop Windows 11 x64 — TBD version/SHA-256 upon acquisition
- Wondershare Filmora Desktop Windows 11 x64 — TBD version/SHA-256 upon acquisition

License notes: only official, authorized local installations. No repacks, no DRM bypass,
no cloud upload of user media, no redistribution of competitor assets/branding.

## Input set (owner-authorized, local only)

- 10 bodybuilding/volleyball clips (owned), 1 reference clip, locally supplied music,
  English + Persian speech samples, portrait + landscape mixtures.
- All inputs recorded by SHA-256 + ffprobe JSON in evidence repo; no third-party media committed.

## Tasks (identical inputs)

1. Import ten sources + reference — elapsed, metadata retained, duplicate/error, memory.
2. 30–60 s vertical sports edit — manual actions, moment selection, beat alignment.
3. Match reference pacing/color/framing — manual vs automated.
4. Trim/cut/undo/redo/seek/sync check.
5. English + Persian captions — RTL shaping, timing, ASS/SRT interop.
6. Dialogue/music balance + loudness — measured via approved FFmpeg, not screenshots.
7. Export 1080×1920 H.264 — duration/fps/audio/artifacts/runtime/memory/watermark/offline.
8. Save/reopen, error recovery, offline repeat — subscription/cloud/model deps.

## Evidence taxonomy per observation

- product/version/edition, artifact SHA-256, env/GPU, input hashes, action sequence,
  screenshot/video/trace, result, limitations, confidence.
- Facts from docs cite URL + retrieval date; not treated as execution evidence.

## Scoring (provisional, pre-observation)

- P0 broken data path / fake success / offline violation / invalid export
- P1 high-value sports edit + accurate Persian captions + reliability
- P2 convenience with benchmark evidence + feasible OSS
- P3 cosmetic parity / effect counts without proven user value

Differentiation hypothesis (offline sports editing + Persian) remains hypothesis until
task-based evidence supports it. C2 observation remains BLOCKED until artifacts available.

## References

- RECOVERY-ROADMAP.md C1 row — acceptance gate
- licenses/THIRD-PARTY.md — allowed redistributable licenses
- scripts/pins.json — pinned artifact hashes (no unpinned downloads)
