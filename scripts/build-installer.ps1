<#
.SYNOPSIS
    Builds CuttingEdgeV2-Setup-v<version>.exe on a Windows build machine.

.DESCRIPTION
    Offline-by-design build:
      1. Verifies every pinned artifact in scripts/pins.json (SHA-256 required).
      2. Downloads artifacts only on the BUILD machine (never at runtime, LOCK-05).
      3. Builds the React frontend, the Python sidecar (PyInstaller, one file) and the Tauri shell.
      4. Packages the NSIS installer and writes a .sha256 next to it.

    The produced installer carries every model, binary and the WebView2 fixed-version
    runtime; nothing is downloaded at runtime.

.PARAMETER UpdatePins
    Downloads the artifacts and writes their SHA-256 into scripts/pins.json.
    Run this once on a trusted network, review the diff, then commit.

.PARAMETER WithoutPinnedBinaries
    CI / smoke mode: skips the pinned FFmpeg, models and WebView2 fixed runtime, and asks
    the NSIS target to use the machine's WebView2. The resulting installer is a real,
    installable build of the app whose media engine resolves FFmpeg from PATH
    (docs/install-guide-v1.0.0-en.md, "Light build"). Use the full run for delivery.

.PARAMETER SkipInstaller
    Stops after the sidecar + shell are built (fast inner loop for verification).

.EXAMPLE
    pwsh -File scripts/build-installer.ps1 -UpdatePins
    pwsh -File scripts/build-installer.ps1
    pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries
#>
[CmdletBinding()]
param(
    [switch]$UpdatePins,
    [switch]$WithoutPinnedBinaries,
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pins = Get-Content (Join-Path $PSScriptRoot 'pins.json') -Raw | ConvertFrom-Json
$tauriConfPath = Join-Path $root 'src-tauri/tauri.conf.json'
$version = (Get-Content $tauriConfPath -Raw | ConvertFrom-Json).version
$delivery = Join-Path $root 'delivery'
New-Item -ItemType Directory -Force -Path $delivery | Out-Null
$binariesDir = Join-Path $root 'src-tauri/binaries'

function Assert-NativeSuccess {
    param([string]$Label)
    if ($LASTEXITCODE -ne 0) {
        Write-Output "::error title=Build step failed::$Label exited with code $LASTEXITCODE"
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Show-CompileErrors {
    param([string]$LogPath, [string]$Label)
    if (-not (Test-Path $LogPath)) { return }
    $matches = Get-Content $LogPath | Where-Object { $_ -match '(error(\[E\d+\])?:)|^(error|warning: unused)' }
    foreach ($line in ($matches | Select-Object -First 8)) {
        Write-Output "::error title=$Label::$line"
    }
}

function Invoke-Step {
    param([string]$Label, [scriptblock]$Action)
    Write-Host "::group::$Label"
    try {
        & $Action
    } catch {
        Write-Host '::endgroup::'
        Write-Output "::error title=Build step failed::$Label -> $($_.Exception.Message)"
        throw
    }
    Write-Host '::endgroup::'
}

function Assert-Prerequisites {
    foreach ($tool in @('node', 'npm', 'cargo', 'python')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Missing prerequisite '$tool'. See docs/install-guide-v1.0.0-en.md (Build section)."
        }
    }
    Write-Host "[ok] toolchain present"
}

function Get-TargetTriple {
    $output = & rustc -vV
    $line = $output | Where-Object { $_ -like 'host:*' } | Select-Object -First 1
    if (-not $line) { throw 'rustc did not report a host triple.' }
    return ($line -replace '^host:\s*', '').Trim()
}

function Get-PinnedArtifact {
    param([string]$Name, [pscustomobject]$Pin)

    if ($Pin.url -like 'bundled-in-*') {
        Write-Host "[skip] $Name ships inside its wheel"
        return
    }
    if ($Pin.url -like 'https://developer.microsoft.com*') {
        Write-Host "[note] $Name must be placed in src-tauri/webview2-fixed-runtime/ manually (docs/bypass-smartscreen.md)."
        return
    }

    $target = Join-Path $root $Pin.target
    $archive = Join-Path $env:TEMP ("ce-" + [System.IO.Path]::GetFileName($Pin.url))
    New-Item -ItemType Directory -Force -Path $target | Out-Null

    if (-not (Test-Path $archive)) {
        Write-Host "[get ] $Name"
        Invoke-WebRequest -Uri $Pin.url -OutFile $archive -UseBasicParsing
    }

    $hash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($UpdatePins) {
        $Pin.sha256 = $hash
        Write-Host "[pin ] $Name -> $hash"
        return
    }
    if (-not $Pin.sha256) {
        throw "No pinned SHA-256 for '$Name'. Run with -UpdatePins once, review the pins.json diff and commit it."
    }
    if ($hash -ne $Pin.sha256.ToLowerInvariant()) {
        throw "SHA-256 mismatch for '$Name': expected $($Pin.sha256), got $hash"
    }
    Write-Host "[ok  ] $Name verified"

    if ($archive -like '*.zip') {
        Expand-Archive -Path $archive -DestinationPath $target -Force
    }
}

Assert-Prerequisites

if ($WithoutPinnedBinaries) {
    Write-Host '[warn] -WithoutPinnedBinaries: FFmpeg/models/WebView2 runtime are NOT embedded.'
} else {
    Get-PinnedArtifact -Name 'ffmpeg' -Pin $pins.ffmpeg
    foreach ($entry in $pins.models.PSObject.Properties) {
        Get-PinnedArtifact -Name $entry.Name -Pin $entry.Value
    }
    if ($UpdatePins) {
        $pins | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $PSScriptRoot 'pins.json') -Encoding utf8
        Write-Host 'pins.json updated. Review and commit before the first real build.'
    }
}

Invoke-Step '[1/4] frontend' {
    Push-Location (Join-Path $root 'frontend')
    try {
        npm ci
        Assert-NativeSuccess 'npm ci'
        npm run build
        Assert-NativeSuccess 'npm run build'
    } finally { Pop-Location }
}

Write-Host '[2/4] python sidecar'
$sidecarTarget = Join-Path $binariesDir ("cutting-edge-backend-" + (Get-TargetTriple) + ".exe")
Push-Location (Join-Path $root 'backend')
try {
    if (-not (Test-Path '.venv')) { python -m venv .venv }
    $py = Join-Path (Get-Location) '.venv/Scripts/python.exe'
    & $py -m pip install --upgrade pip
    & $py -m pip install -r requirements.txt
    & $py -m pip install pyinstaller==6.22.3
    & (Join-Path (Get-Location) '.venv/Scripts/pyinstaller.exe') --noconfirm --clean packaging/sidecar.spec
    Assert-NativeSuccess 'pyinstaller'
} finally { Pop-Location }

$builtSidecar = Join-Path $root 'backend/dist/cutting-edge-backend.exe'
if (-not (Test-Path $builtSidecar)) { throw "sidecar executable not produced at $builtSidecar" }
New-Item -ItemType Directory -Force -Path $binariesDir | Out-Null
Copy-Item $builtSidecar $sidecarTarget -Force
$sidecarSize = [math]::Round((Get-Item $sidecarTarget).Length / 1MB, 1)
Write-Host "[ok  ] sidecar staged ($sidecarSize MB) -> $sidecarTarget"

# tauri-build copies FixedRuntime into resources during cargo build, not just bundling.
# Apply light-mode configuration BEFORE both builds and restore it even on failure.
$confBackup = Get-Content $tauriConfPath -Raw
try {
    if ($WithoutPinnedBinaries) {
        $conf = $confBackup | ConvertFrom-Json
        $conf.bundle.windows.webviewInstallMode = [pscustomobject]@{ type = 'skip' }
        $conf | ConvertTo-Json -Depth 12 | Set-Content $tauriConfPath -Encoding utf8
        Write-Host '[note] Light build uses the machine WebView2 runtime throughout compilation and packaging.'
    }

    Write-Host '[3/4] tauri shell'
    Push-Location (Join-Path $root 'src-tauri')
    try {
        $cargoLog = 'cargo-build.log'
        cargo build --release --message-format=short 2>&1 | Tee-Object -FilePath $cargoLog
        if ($LASTEXITCODE -ne 0) {
            Show-CompileErrors -LogPath $cargoLog -Label 'cargo build'
            # Custom build-script failures explain the cause after the headline error.
            # Keep this context in check annotations when artifact downloads are unavailable.
            $context = (Get-Content $cargoLog -Tail 45) -join '%0A'
            Write-Output "::error title=cargo build context::$context"
        }
        Assert-NativeSuccess 'cargo build'
    } finally { Pop-Location }

    if ($SkipInstaller) {
        Write-Host '[4/4] skipped installer (-SkipInstaller)'
    } else {
        Write-Host '[4/4] nsis installer'
        Push-Location (Join-Path $root 'src-tauri')
        try {
            $tauriLog = 'tauri-build.log'
            npx --yes @tauri-apps/cli@2 build --bundles nsis 2>&1 | Tee-Object -FilePath $tauriLog
            if ($LASTEXITCODE -ne 0) { Show-CompileErrors -LogPath $tauriLog -Label 'tauri build' }
            Assert-NativeSuccess 'tauri build'
        } finally { Pop-Location }
    }
} finally {
    Set-Content -Path $tauriConfPath -Value $confBackup -Encoding utf8
}

if ($SkipInstaller) { exit 0 }

$built = Get-ChildItem -Path (Join-Path $root 'src-tauri/target/release/bundle/nsis') -Filter '*.exe' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $built) { throw 'NSIS installer was not produced.' }

$final = Join-Path $delivery ("CuttingEdgeV2-Setup-v$version.exe")
Copy-Item $built.FullName $final -Force
$hash = (Get-FileHash $final -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$final.sha256" -Value "$hash  CuttingEdgeV2-Setup-v$version.exe" -Encoding ascii

$sizeMb = [math]::Round((Get-Item $final).Length / 1MB, 1)
Write-Host "`n[delivered] $final"
Write-Host "[size     ] $sizeMb MB (delivery budget 3.5 GB with models and FFmpeg)"
Write-Host "[sha256   ] $hash"
