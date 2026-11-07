# Evidence Report — R2c packaged desktop transport/resource loop

2026-11-05 · same branch / PR #1 · Owner merges; no merge performed.

**Release remains BLOCKED.** Historical authored work is **260/260 = 100%**, not an
installer-readiness percentage. This report separates real source CLI/browser,
frozen Windows, installed native-window and actual WebView acceptance.

## Inspect → reuse → minimal integration

Production React used relative `/api/v1` and media URLs, but Tauri originally displayed
an embedded page with no production proxy. The shell accepted any listening TCP service,
dropped sidecar events, and did not explicitly clean up its Rust-owned child on exit.
Build resources also had no agreed frontend/native/model layout.

Reused **Starlette StaticFiles**, **Uvicorn Config/Server**, **Pydantic**, existing
**serde_json**, **tauri-plugin-shell 2.6.0**, **PyInstaller onedir**, Tauri resource maps
and the existing NSIS build. No added Python/frontend runtime dependency, detector,
training, custom HTTP parser, external runtime service or imported n8n workflow.

- Serve only `frontend/` after the API routes, on the backend origin. Existing frontend
  API/media URLs stay relative. Unknown API routes remain 404, not successful SPA HTML.
  Install dependencies, models, logs and parent files are not a static-file root.
- Native launch sets `CUTTING_EDGE_HOME` from Tauri's resource directory. Mapped resources
  have `frontend/`, `binaries/ffmpeg/bin/`, `models/`, and PyInstaller `_internal/` at known
  installed paths. Light staging is reset so stale full-build assets cannot leak into it.
- PyInstaller now uses **onedir**, with its dependency directory explicitly carried by
  Tauri resources. This avoids per-launch onefile extraction/bootloader lifetime concerns;
  it is not a claim that a onefile temporary-directory leak was measured in this loop.
- The desktop CLI owns its loopback listening socket **before** publishing startup state.
  Windows uses exclusive-address binding. A per-launch, atomically published JSON receipt
  identifies the launch, origin and resource home after DB/inspection initialization.
  Native Rust checks an at-most-4-KiB receipt **and** TCP reachability and drains child events.
  A stale receipt or arbitrary listening service alone cannot establish readiness.
- The receipt is **correlation, not authentication**. Managed desktop requests enforce the
  exact Host/Origin, cross-site rejection and self-only CSP. Bundled `data:` fonts are
  allowed; external script/connect/font origins are not. The standalone preview remains
  proxy-compatible and has a separate, intentionally unmanaged boundary.
- A bundled bilingual startup/error page precedes native navigation. The loopback frontend
  has no remote Tauri IPC or JS shell permission. Native navigation is allowlisted.
- Rust-owned sidecars explicitly use OSS plugin process groups / Windows Job Objects and
  kill-on-drop, drain events and clean up on orderly exit. **This plugin's Job Object does
  not set KILL_ON_JOB_CLOSE. Abrupt shell-death OS containment is still OPEN.**

## Actual local acceptance

| Gate | Observed result |
|---|---|
| Backend lint + format | PASS |
| Backend with provisioned native/librosa adapters | **333 PASS**, **93.97%**, 20.58 s |
| Frontend lint / tests / tsc / production build | **168 PASS**, 20 files; build 5.04 s |
| Source CLI, manually mapped test home, no Vite | **27/27 PASS** |
| Real built React + API + media browser | **22/22 PASS** |
| Original primary data | All rows in four tables unchanged; no QA imports |

The CLI gate actually binds a socket and starts Uvicorn, tests two launches in a
Unicode/space-containing resource/profile path, real HTTP/API/CSP, foreign Host/Origin,
private-file isolation, occupied-port failure, missing-frontend failure and local errors.
It is explicitly **source-cli**, not a local frozen-binary claim.

The browser gate actually imports/probes an owned H.264 fixture, decodes/advances source
playback, verifies range bytes, saves/reloads the actual SQLite timeline/project and
switches English/Persian RTL. **No Vite client, external HTTP, observed page errors or
browser console errors.** This is source playback, not a rendered edit.

[English built UI](evidence/desktop-r2c/built-ui-en.png) ·
[Persian built UI](evidence/desktop-r2c/built-ui-fa.png) ·
[browser checks](evidence/desktop-r2c/browser.json) ·
[CLI checks](evidence/desktop-r2c/smoke.json) ·
[backend output](evidence/desktop-r2c/backend-native.log) ·
[frontend output](evidence/desktop-r2c/frontend-verification.log) ·
[primary preservation](evidence/desktop-r2c/primary-data-preservation.json).

## Windows loop: failures retained, not hidden

1. **f7f2681 / push 41978911805:** real Windows Rust/NSIS build and the actual frozen
   executable/resource/HTTP gate passed **27/27**. Silent NSIS installation and native
   sidecar launch also passed, but the installed test failed at literal resource-path
   comparison. This encompassing run is **FAILURE**, not installer acceptance.
2. **903f6d6 / push 41980922410:** logged both paths. Tauri returned the real extended
   `\\?\C:\Users\runneradmin\...` path; TEMP used the `RUNNER~1` alias. Even Path.resolve
   equality retained the extended-path distinction. This test also failed honestly.
   The harness now uses the OS's **os.path.samefile** on existing directories/files and
   checks the `models` leaf separately, rather than comparing spelling or removing a
   prefix with an ad-hoc parser.
3. **908bb59 / push 41982954804 — FAILURE:** build, production readiness-module
   tests, frozen **27/27**, NSIS installation, resource/profile identity, served React
   and native window passed. Actual WebView attachment failed immediately with
   `ECONNREFUSED 127.0.0.1:9222`; DOM/screenshot and orderly-close gates were not reached.
4. **83179cc / push 41995097569 — FAILURE:** a bounded 30-second IPv4/IPv6 retry
   still found no CDP listener. Earlier real install/HTTP/window checks passed again.
   This was not merely a proven startup race. Per-check notices exhausted GitHub's
   annotation quota, so this revision did not expose the intended browser flags.
5. **4d4a639 / push 41997214939 — VERIFIED SUCCESS:** official Microsoft
   documentation and Wry issue 1782 explain Runtime >=150 ignoring env/HKCU debug
   overrides in elevated hosts such as GitHub Windows runners. The harness now opts
   into **app-specific HKLM** test policy only on disposable GitHub Windows runners,
   restoring existing keys/values/types, closing handles and restoring in `finally`
   with fail-on-restore-error; no wildcard, product debug flag, custom token
   manipulation or new runtime dependency. **20/20 installed-native checks and 11/11
   actual WebView checks PASS.** Native page `http://127.0.0.1:8756/` passed: connected
   workspace, Persian RTL, relative healthy API, no Vite, observed local resources,
   no page/console errors, screenshot `installed-webview-fa.png` **86057 bytes, SHA256
   b12045625662b7f885301d6d04d50a3ab0c977dc32e97d1feefd1919494b32f4** captured, independent
   orderly native window close and owned backend cleanup within 20s, and test-only HKLM
   policy `restored:true` for `com.cuttingedge.v2` / `cutting-edge-v2.exe`. The UI and
   orderly-cleanup gates run independently; a UI failure still fails the encompassing
   job. This is a real installed WebView/native-cleanup gate, not full delivery
   acceptance. Full models/pins/licenses/fixed runtime/offline/render gates remain OPEN.

Windows frozen checks were recovered from their actual Actions artifacts using a read-only
runner job and GitHub check annotations; direct artifact/log download redirects are not
reachable from this sandbox (blob storage egress blocked). Raw recovery annotations and
failed runs are retained under
[evidence/desktop-r2c/windows-first](evidence/desktop-r2c/windows-first/) and
[evidence/desktop-r2c/windows-path-diagnostic](evidence/desktop-r2c/windows-path-diagnostic/),
[windows-cdp-first](evidence/desktop-r2c/windows-cdp-first/),
[windows-cdp-retry](evidence/desktop-r2c/windows-cdp-retry/) and the verified
[windows-native](evidence/desktop-r2c/windows-native/) run/annotations/summaries.
Earlier plain-JSON ANSI error transport was malformed; d68 now exposes structured
`installed.json` / `webview.json` / `smoke.json` via standard base64 JSON annotations
(`≤65536` input, `≤60000` encoded) which verify without repair. PNG base64 chunks of
`64000` chars were truncated by GitHub's `~4096`-char notice limit (unterminated JSON
at char 189); d68 now emits **metadata only** (bytes/SHA/artifact link) and links to the
artifact `https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./actions/runs/41997214939/artifacts/13401078754`
for the actual image. Valid installed/frozen records were recovered separately and are not
repaired by a custom parser.

The exact production readiness module is tested by a tiny standalone Cargo harness, not
a copied implementation. This avoids recompiling the whole GUI dependency graph in the
separate unwind-enabled test profile; Windows 908bb59 and 4d4a639 actually passed it. The
workflow previously used manual `actions/cache/restore|save` over `C:\build\src-tauri\target` which warned
**Cache save failed** (`C:\Program` / GNU tar exit 2) from long Windows paths/locks; replaced with OSS `Swatinem/rust-cache@v2` (MIT) that caches `~/.cargo` + workspaces `C:\build\src-tauri -> target` correctly and saves automatically on push. Build speed is not release acceptance; actual 12m17s build observed. The new `windows-pin-guards.ps1` negative contract (null hash, malformed hash,
missing target → fail before file/network via AST of real `Get-PinnedArtifact`) is enforced
before network and verified PASS on Windows in d68. No compiler speedup is claimed.

## Observed corrections and limitations

- First source CLI integration used an unsupported `uvicorn.run(sockets=...)` argument;
  the real subprocess test caught it. Switched to public `Server.run(sockets=...)`.
- First browser attempt exposed CSP-blocked bundled data-font resources; fixed and covered
  by a regression assertion. The native MPEG-4 Part 2 stimulus was not browser-decodable;
  transport playback is tested with the existing owned H.264 fixture instead. General
  codec/proxy support remains OPEN, not silently treated as universal playback.
- A local Linux freeze attempt was blocked by missing `libpython3.11.so.1.0`; actual
  frozen acceptance is therefore from Windows CI, not inferred from source tests.
- `workflow_dispatch` returned integration permission HTTP 403. Ordinary pushes, read-only
  CI evidence recovery and PR CI still work. GitHub connection/permissions need attention
  for manual dispatch; no credentials were requested or stored.

## External implementation evidence (retrieved 2026-11-05)

- [Microsoft elevated-host override policy](https://github.com/MicrosoftDocs/edge-developer/blob/main/microsoft-edge/webview2/concepts/security.md#for-an-elevated-host-app-use-appropriate-override-flags): env/HKCU ignored, HKLM/API honored.
- [Microsoft Runtime-150 report / response](https://github.com/MicrosoftEdge/WebView2Feedback/issues/5645): same remote-debug-port symptom and supported overrides.
- [Wry Windows runner reproduction](https://github.com/tauri-apps/wry/issues/1782): independent evidence; not proof of our final acceptance.
- [Official WebView2 Win32 registry semantics](https://github.com/MicrosoftDocs/webview2-win32-reference/blob/main/1-0-3537-50/webview2-idl.md#createcorewebview2environmentwithoptions): AUMID then executable-name lookup; wildcard avoided.

## Remaining release gates — not cleared by these tests

- Actual latest installed WebView/native cleanup result; full fixed-runtime clean/offline
  installation, uninstall/update and cold restart on the target Windows environment.
- Independent native **abrupt shell-death** supervision and actual native-worker crash
  coverage. The plugin's ordinary group cleanup is not kernel kill-on-close containment.
  `win32job` 2.0.3 (MIT/Apache-2.0) was researched as a safe OSS option, **not added or proven**.
- Verified model artifacts/URLs/SHA-256, per-weight/per-voice redistribution licensing,
  optional inference/phonemizer runtime audit, fixed WebView2 artifact/signature/pin.
  Placeholder/null pins still block the full bundle; a light setup is not the delivery.
- Genuine pretrained analysis → StyleDNA → EDL → approved renderer/export, actual edited
  preview, authorized sports/music/Persian-caption quality and resource/performance gates.
- Local API authorization/multi-user threat review; Host/Origin checks are not local-client
  authentication. Strong blocked-I/O deadlines, unknown/legacy cache policy and power-loss
  behavior remain separate from the nominal startup poll timeout.
- Locked native dependency graph/reproducibility, complete bundled-license inventory,
  FFmpeg DLL/adapter placement in a **full** bundle, NVENC/approved fallback and clean offline
  acceptance. No libx264/GPL runtime was introduced by this work.

## Reproduce / inspect

```bash
cd backend
CE_ANALYSIS_TESTS=1 CE_SCENE_NATIVE_TESTS=1 \
CE_SCENE_HOME=/tmp/ce-r2c-home CE_SCENE_FIXTURES=/tmp/ce-r2c-fixtures \
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

```bash
backend/.venv/bin/python scripts/ci/desktop-sidecar-smoke.py --python-module \
  --executable backend/.venv/bin/python --home /tmp/ce-desktop-home \
  --output /tmp/ce-desktop-source-smoke
NODE_PATH=/home/user/ce-test-tools/node_modules \
LD_LIBRARY_PATH=/home/user/ce-test-tools/al2023/lib \
node scripts/local-tests/desktop-transport.cjs
```

Git log/diffstat and final revision/CI provenance are recorded with the evidence when this
loop is finalized. Historical 260/260 authored progress is unchanged; **no release-ready
notification or automatic PR merge is justified**.
