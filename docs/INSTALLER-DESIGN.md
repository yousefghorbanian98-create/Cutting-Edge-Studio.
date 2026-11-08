# Staged Windows installer — design and verification

Implements the multi-stage, game-style setup: detect prerequisites, install what is
missing, prove it took effect, install the app, then verify what landed — all reported
into one continuous progress view.

Files: `src-tauri/installer-hooks.nsh`, `src-tauri/tauri.conf.json`,
`scripts/pins.json`, `scripts/build-installer.ps1`.
Enforced by `backend/tests/test_installer_contract.py` (15 tests).

## Why hooks and not a custom NSIS template

Tauri v2 exposes `bundle.windows.nsis.installerHooks`, a `.nsh` file whose macros are
spliced into the generated `installer.nsi`. The alternative — replacing the whole
template — means owning a 1000-line upstream file forever and re-merging it on every
Tauri upgrade.

The hook file therefore **only adds** what Tauri does not do. It deliberately does not
touch WebView2 installation, file copying, shortcuts, the registry or the uninstaller,
because the generated installer already owns those. A test asserts this boundary so a
future edit cannot quietly start fighting the template:

```python
assert "createshortcut" not in body    # shortcut creation belongs to Tauri
assert "writeuninstaller" not in body  # the uninstaller belongs to Tauri
```

## The five stages

Each stage prints into the single INSTFILES details view, so the user watches one list
fill in rather than clicking through dialogs.

```
==============================================
 CuttingEdgeV2 1.0.0 - staged installation
==============================================
[1/5] Checking system requirements
        OK    Architecture: x64
        OK    Windows build 22631
        OK    CPU supports AVX2
        OK    Installed RAM: 16384 MB
        OK    Free space on C:: 48210 MB
[2/5] Checking Visual C++ 2015-2022 x64 runtime
        ..    Not present. Installing the bundled runtime.
        ..    Running vc_redist.x64.exe /quiet /norestart
        OK    Runtime installer finished (exit 0).
[3/5] Verifying prerequisites
        OK    Visual C++ x64 runtime present 14.44.x
        OK    WebView2 runtime detected: 141.0.x
[4/5] Installing application files
        ... Tauri copies the payload ...
[5/5] Verifying the installed application
        OK    CuttingEdgeV2.exe
        OK    cutting-edge-backend.exe (processing sidecar)
        OK    frontend\index.html (user interface)
        OK    _internal (frozen Python runtime)
        OK    Wrote install-report.txt
==============================================
 Finished: all 5 stages completed cleanly.
==============================================
```

### Stage 1 — system requirements

Checks are taken from `docs/COMPATIBILITY.md` rather than invented:

| Check | Source | Behaviour |
|---|---|---|
| x64 | ARM/32-bit "not supported" | **blocks** |
| Windows 10 21H2 (build 19044) | supported matrix | blocks below Win10; warns below 19044 |
| CPU AVX2 | "CPU minimum: 4 cores, AVX2" | **blocks** |
| RAM ≥ 8 GB | hardware minimum | warns |
| Free disk ≥ 6 GB | "6 GB free (full build)" | **blocks** |

AVX2 is the check a generic installer would miss: MediaPipe and onnxruntime crash at
first use without it, which would otherwise surface as a mystery failure long after
setup "succeeded".

### Stage 2 — prerequisite installation, offline

The frozen Python sidecar links against the Visual C++ 2015-2022 x64 runtime. The
redistributable is **embedded at build time** and executed from `$PLUGINSDIR`:

```
ExecWait '"$PLUGINSDIR\vc_redist.x64.exe" /quiet /norestart' $1
```

Exit codes are interpreted rather than ignored — `0` installed, `1638` a newer runtime
is already present, `3010` installed but a reboot is queued (sets the reboot flag),
anything else aborts with the code shown.

**Nothing is downloaded at install time.** The product's offline lock (README: "no
telemetry, CDN or automatic downloads") would be broken by the usual
bootstrapper-downloads-the-redist pattern, so the payload is pinned by SHA-256 in
`scripts/pins.json` and fetched on the *build* machine only. A test enforces this:

```python
forbidden = ("inetc::", "NSISdl::", "INetLoad::", "http://", "https://", "DownloadFile")
```

If the payload was not staged (the `-WithoutPinnedBinaries` light build), the hook
compiles without it and reports the prerequisite instead of pretending — it never
reaches for the network as a fallback.

### Stage 3 — verification, not assumption

A silent installer that returns 0 without registering is a classic failure. The runtime
is therefore re-read from the registry *after* installation, under both the native and
WOW6432Node views so the result does not depend on the installer's own bitness. If it
still does not register, setup aborts rather than producing a broken install.

### Stage 5 — verify what actually landed

Missing main binary or missing sidecar abort the install; a missing UI or `_internal`
directory warns. A `install-report.txt` is written for support.

## Build wiring

`scripts/build-installer.ps1` stages the payload with the same pinned-artifact path
used for FFmpeg and the models, then exports the directory the hook reads at compile
time:

```powershell
$env:CE_PREREQ_DIR = $prereqDir   # or '' for the light build
```

`src-tauri/prerequisites/` is gitignored, so the Microsoft binary is never committed.

## What is verified, and where

| Check | Where |
|---|---|
| hooks defined, macros/functions/LogicLib/preprocessor balanced | `test_installer_contract.py` |
| no network access from the installer | `test_installer_contract.py` |
| no duplication of Tauri-owned behaviour | `test_installer_contract.py` |
| stage counter matches `CE_TOTAL_STAGES` | `test_installer_contract.py` |
| pure ASCII (the script compiles with `Unicode true`; a BOM-less UTF-8 include would be read as ANSI and garble user-visible text) | `test_installer_contract.py` |
| prerequisite is SHA-256 pinned and gitignored | `test_installer_contract.py` |
| **NSIS actually compiles** | `installer` job on `windows-latest` |
| **installer runs and the app launches** | `installer` job, "Install and launch native desktop" |

### Honest limitation

NSIS cannot be compiled in this Linux sandbox — there is no `makensis` and the Debian
archives are outside the network allowlist. The static tests above are therefore a
pre-filter, not a substitute: the authoritative check is the Windows `installer` job,
which already builds the bundle and installs it. The hook script has not yet been
executed on a Windows machine.

`scripts/pins.json` ships `vc_redist_x64.sha256 = null`, and the build script refuses
to build while a hash is null. An operator must run
`pwsh -File scripts/build-installer.ps1 -UpdatePins` once on a trusted network, review
the diff and commit the pin before the first full delivery build.

## Silent installs must never open a dialog

CI installs the bundle headlessly with `/S /D=<dir>` and waits for the process to
exit (`scripts/ci/windows-installed-desktop.ps1`). NSIS still renders a `MessageBox`
under `/S`, so an unguarded dialog does not fail the install, it *suspends* it: the
first version of these hooks hung the Windows job for over an hour until the runner
timed out, with no error anywhere in the log.

Every failure path therefore goes through one macro:

```nsis
!macro CE_Abort TEXT
  !insertmacro CE_Fail "${TEXT}"
  ${IfNot} ${Silent}
    MessageBox MB_ICONSTOP|MB_OK "${TEXT}"
  ${EndIf}
  SetErrorLevel 2
  Abort "${TEXT}"
!macroend
```

An interactive user still gets the dialog; an automated caller gets exit code 2 and
the reason in `$INSTDIR\install-report.txt`. `test_installer_contract.py` fails the
build if any `MessageBox` appears outside a `Silent` guard, or if `CE_Abort` stops
setting an exit code, so this cannot regress silently.

For the same reason stage 5 does not hard-code the sidecar's filename. Tauri strips
the target triple from `externalBin`, but the check falls back to a
`cutting-edge-backend*.exe` wildcard before it declares the payload incomplete.

## Getting a built installer

The installer is built by the `installer` job on `windows-latest`; that job is the
only place where `makensis` actually compiles `installer-hooks.nsh`. Every run
uploads the result as the `CuttingEdgeV2-Setup` artifact, which is retained for the
repository's artifact window and requires a GitHub login to download.

To produce a permanent, public download link, push a version tag:

```sh
git tag v1.0.0-light
git push origin v1.0.0-light
```

The `release` job then attaches the `.exe` and its `.sha256` to a GitHub Release.
It reuses the artifact the `installer` job already produced rather than building a
second time, and it is the only job granted `contents: write` — the permission is
scoped to tag pushes and to an explicit `workflow_dispatch` that names a tag, so it
is never active on an ordinary branch push.

Note that `concurrency.cancel-in-progress` is on and keyed to the ref. Pushing to a
branch while its Windows build is running cancels that build before the artifact is
uploaded. Tags get their own concurrency group, so a release build is not affected
by branch activity.

## The pinned-tool download is an availability risk, not a trust one

The Windows job verifies the real FFmpeg tooling against a reviewed SHA-256 in
`scripts/pins.json` before the installer is built. That archive is served from the
upstream release CDN, which has been observed returning HTTP 504 for sustained
periods — measured at 0 successes in 6 attempts from outside CI, and 0 in 8 inside
it, for the same asset that was downloading normally an hour earlier.

Two mitigations, in order:

1. `actions/cache`, keyed by the reviewed hash (`ce-ffmpeg-<sha256>`). A changed pin
   cannot collide with a stale entry.
2. A deadline-bounded retry, ten minutes, for the cold-cache case.

The bundler has the same exposure: `tauri-bundler` downloads `nsis-3.13.zip` from
a GitHub release when it packages the app, with no retry of its own. A build that
had already produced `cutting-edge-v2.exe` still died with
`failed to bundle project: http status: 504`. That toolchain is cached under
`~\AppData\Local\tauri` for the same reason.

Neither relaxes verification. The checksum is re-checked on whatever the cache
returns and again on anything downloaded, so an outage can delay a build but can
never cause an unverified binary to be used. If the pin ever needs to move, update
`pins.json` and the cache key follows automatically.
