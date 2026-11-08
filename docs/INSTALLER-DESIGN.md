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
