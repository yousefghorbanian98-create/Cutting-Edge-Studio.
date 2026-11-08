# Frontend ↔ Backend Coupling Review — 2026-11-08

> **Status:** C1, C2 and C5 are fixed, C4 was verified to be a non-defect, and C3 is
> partially reduced — see [`ECC-FIXES-2026-11-08.md`](./ECC-FIXES-2026-11-08.md).
> One figure below was corrected on review: the post API has **12** operations, not 9.

Method: ECC `fastapi-reviewer` + `typescript-reviewer` + `architect` rubrics, applied as a
two-way contract diff between the live FastAPI OpenAPI schema (64 routes) and every call site in
`frontend/src`, then confirmed dynamically by driving the real UI in a headless browser against
the real backend.

Screenshots: `docs/evidence/ui-review-2026-11-08/`. Live API trace: `api-trace.json`.

## 1. How the two sides are coupled

The coupling is **indirect and proxied by design** — the browser never addresses the backend:

```
browser ──relative /api/v1/*──► Vite dev server ──proxy──► 127.0.0.1:8756 FastAPI
```

`frontend/src/lib/api.ts:25` fixes `const BASE = '/api/v1'` and every request is relative.
`vite.config.ts` proxies `/api` to `CUTTING_EDGE_BACKEND`, with the rationale in a comment:
*"The browser never talks to it directly: Vite proxies /api so the UI works under any preview
host without CORS surprises."*

The backend enforces the other half: `app/__main__.py:36` refuses to start on any host other
than `127.0.0.1`, and `app/desktop.py:53` validates the `Host` header.

A single `request<T>()` helper (`api.ts:27`) is the only `fetch` call site in the application.

## 2. Static contract diff

| Direction | Result |
|---|---|
| Frontend calls → backend routes | **33/33 resolve. Zero broken calls.** |
| Backend routes → frontend callers | **30 of 64 routes (47%) have no caller** |

Four job families are reached through one parameterised client rather than hard-coded paths —
`api.ts:73`:

```ts
const measurementPath = (operation: InspectionOperation) =>
  ({decode:'inspection', rhythm:'rhythm', scenes:'scenes', analysis:'analysis'})[operation];
```

`InspectionOperation` is a closed TS union, so adding a family is a compile-time change on the
frontend and a router change on the backend. This is the healthiest part of the coupling: one
typed client covers 20 routes without duplication.

## 3. Runtime verification

Driving the real UI against the real sidecar (11 real H.264 files, generated with ffmpeg):

```
200 GET  /api/v1/health
201 POST /api/v1/projects
200 GET  /api/v1/projects/{id}/workspace
201 POST /api/v1/projects/{id}/uploads
206 GET  /api/v1/assets/{id}/content     × 11   (byte-range streaming)
200 PUT  /api/v1/projects/{id}/workspace          (autosave)
```

29 requests, **zero non-2xx/3xx responses, zero page errors**. Byte-range `206` responses confirm
`FileResponse` range support is exercised end to end. Backend `ffprobe` metadata appears verbatim
in the UI (`65 KB · 4.00s · 640×360`; reference `4.4 MB · 12.00s · 1280×720`), so the two sides
agree on real decoded values, not placeholders.

Verdict: **the wired paths are correctly and tightly coupled.** The defects below are about
surface that is *not* wired.

## 4. Findings

### C1 — The entire post-production feature is disconnected · severity HIGH

Backend implements 12 `/api/v1/post/*` operations across 11 paths (`api/post.py`, 216
lines, plus 841 lines of services) and they work — `GET /post/presets` returns real data, `/post/layouts` and
`/post/templates` return 200.

The frontend renders `PostPanel.tsx` (154 lines) driven by `postStore.ts` (126 lines) and shows
seven post-production toggles plus a platform selector (visible in every screenshot).

**There is no connection between them.** `api.ts` exposes no post client; `postStore.ts` and
`PostPanel.tsx` contain zero API calls. The panel is pure client-side state.

Worse, the two sides **duplicate the same data**. `postStore.ts` hardcodes the preset table that
the backend also owns:

| preset | frontend (`postStore.ts`) | backend (`GET /post/presets`) |
|---|---|---|
| tiktok | 1080×1920, max 180s | 1080×1920, fps 30 |
| shorts | 1080×1920, max 60s | 1080×1920, fps 30 |
| youtube | 1920×1080, max null | 1920×1080, fps 30 |
| instagram_feed | 1080×1350, max 60s | 1080×1350, fps 30 |
| archive | 3840×2160, max null | 3840×2160, fps 30 |

They agree **today**, by manual discipline — no test enforces it, and the backend additionally
owns `fps`, `bitrate_kbps` and the ffmpeg `options` array that the frontend does not model. Any
future edit to one side drifts silently, and the UI will keep showing toggles that change
nothing.

Fix: have `PostPanel` fetch `/post/presets` and `/post/layouts` and delete the hardcoded tables,
or state explicitly in the UI that post-production is not yet wired.

### C2 — NVENC is reported available on machines with no NVIDIA GPU · severity HIGH

`GET /api/v1/media/encoder` on this GPU-less Linux box returns:

```json
{"encoder":"h264_nvenc","hardware":true,"note":"NVENC H.264 only (no AV1/B-frames on Turing)"}
```

There is no NVIDIA device present (`nvidia-smi` absent, no `/dev/nvidia*`). An actual encode with
that encoder fails:

```
[h264_nvenc @ …] Cannot load libcuda.so.1
[vost#0:0/h264_nvenc @ …] Error while opening encoder
```

Root cause — `services/media/ffmpeg.py:78`:

```python
def available_h264_encoder(encoders: set[str]) -> str | None:
    """Pick the first allowed H.264 encoder that the build actually ships."""
    return next((name for name in H264_ENCODERS if name in encoders), None)
```

Detection parses `ffmpeg -encoders` and takes the first match from
`H264_ENCODERS = ("h264_nvenc", "libopenh264")`. That tests whether the **build was compiled**
with NVENC, never whether the encoder can be **opened at runtime**. Any ffmpeg built with NVENC
support reports hardware acceleration regardless of the GPU.

Impact on the shipped Windows app: on a machine with no NVIDIA card, a disabled/hybrid GPU, or a
driver mismatch, the UI advertises hardware encoding and render jobs select `h264_nvenc`, then
fail with a raw ffmpeg error instead of falling back to `libopenh264`.

Why 565 tests missed it: the suite feeds a synthetic `-encoders` string from `tests/fixtures.py:45`
and asserts `available_h264_encoder(encoders) == "h264_nvenc"` (`test_media_ffmpeg.py:46`). The
tests assert the implementation, not the requirement, and never attempt an encode.

Fix: after selecting an encoder, probe it for real once
(`ffmpeg -f lavfi -i nullsrc -t 0.1 -c:v h264_nvenc -f null -`) and fall back to `libopenh264` on
failure. Cache the result.

### C3 — 30 of 64 backend routes have no frontend caller · severity MEDIUM

Beyond the 9 post routes in C1, these are implemented, reachable and unused by the UI:

```
GET    /api/v1/settings                              GET  /api/v1/system/diagnostics
GET    /api/v1/jobs          GET /api/v1/jobs/{id}   GET  /api/v1/media/encoder
GET    /api/v1/projects/{id}                         PATCH /api/v1/projects/{id}
DELETE /api/v1/projects/{id}                         POST /api/v1/assets/{id}/proxy
GET    /api/v1/projects/{id}/render/encoder
GET    /api/v1/projects/{id}/stylematch/artifacts[/{kind}]
GET    /api/v1/projects/{id}/stylematch/edl/validate
POST   /api/v1/projects/{id}/stylematch/{dna,edl,reference,score}
POST   /api/v1/projects/{id}/assets
```

Notably the **entire Style Match write path** (`dna`, `edl`, `reference`, `score`) is unreachable
from the UI, even though Style Match is the headline feature and its wizard is rendered. This is
consistent with the README's "StyleDNA-to-render orchestration … not accepted", so it is expected
rather than surprising — but it quantifies the gap: **47% of the API is not consumed**, and
`DELETE /projects/{id}` means projects can be created from the UI but never deleted.

`GET /api/v1/assets/{id}/content` is *not* in this list — it is consumed as a direct media `src`
in `RenderPanel.tsx:157`, which my first pass wrongly flagged.

### C4 — Duplicate `/health` request on every mount · severity LOW

The load trace shows `GET /api/v1/health` twice. Expected under React 18 StrictMode double-effect
in dev, but worth confirming the health poll is cleaned up in its `useEffect` teardown so it does
not double in production builds.

### C5 — No contract test binds the two sides · severity MEDIUM

Backend Pydantic models and frontend TS interfaces/zod schemas are written independently. There
is no OpenAPI-derived type generation and no test that fails when a response model changes shape.
`api.ts` declares `HealthResponse`, `ProjectResponse`, `AssetResponse` and others by hand.

The zod schemas in `inspectionSchema.ts` do validate at runtime, which is a genuine safety net for
the inspection family — but it is applied to only part of the surface, and a backend field rename
elsewhere would surface as a runtime `undefined` rather than a failing build.

Fix: generate types from `/openapi.json` in CI and fail on drift, or extend zod validation to all
responses.

## 5. Summary

The coupling is **architecturally sound and correct where it exists**: one typed client, one proxy
hop, relative URLs only, loopback enforced on both ends, 33/33 frontend calls resolving, and a
clean 29-request runtime trace with zero errors.

The problem is not wrong coupling — it is **absent coupling**. Roughly half the backend is not
reachable from the UI, and in the one place where the frontend does model backend-owned data
(post-production presets) it duplicates it instead of fetching it. C2 is independent of all that
and is a genuine runtime defect that will bite real users on non-NVIDIA hardware.
