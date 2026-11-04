<#
.SYNOPSIS
    Builds CuttingEdgeV2-Setup-<version>.exe on a Windows build machine.

.DESCRIPTION
    Offline-by-design build:
      1. Verifies every pinned artifact in scripts/pins.json (SHA-256 required).
      2. Downloads artifacts only on the BUILD machine (never at runtime, LOCK-05).
      3. Builds the React frontend, the Python sidecar and the Tauri shell.
      4. Packages the NSIS installer and writes a .sha256 next to it.

    Runtime downloads stay impossible: the produced installer carries every model,
    binary and the WebView2 fixed-version runtime.

.PARAMETER UpdatePins
    Downloads the artifacts and writes their SHA-256 into scripts/pins.json.
    Run this once on a trusted network, review the diff, then commit.

.PARAMETER SkipInstaller
    Stops after the sidecar + shell are built (fast inner loop for verification).

.EXAMPLE
    pwsh -File scripts/build-installer.ps1 -UpdatePins
    pwsh -File scripts/build-installer.ps1
#>
[CmdletBinding()]
param(
    [switch]$UpdatePins,
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pins = Get-Content (Join-Path $PSScriptRoot 'pins.json') -Raw | ConvertFrom-Json
$version = (Get-Content (Join-Path $root 'src-tauri/tauri.conf.json') -Raw | ConvertFrom-Json).version
$delivery = Join-Path $root 'delivery'
New-Item -ItemType Directory -Force -Path $delivery | Out-Null

function Assert-Prerequisites {
    foreach ($tool in @('node', 'npm', 'cargo', 'python')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Missing prerequisite '$tool'. See docs/install-guide-v1.0.0-en.md (Build section)."
        }
    }
    Write-Host "[ok] toolchain present"
}

function Get-PinnedArtifact {
    param([string]$Name, [pscustomobject]$Pin)

    if ($Pin.url -like 'bundled-in-*') {
        Write-Host "[skip] $Name ships inside its wheel"
        return
    }
    if ($Pin.url -like 'https://developer.microsoft.com*') {
        throw "WebView2 fixed-version runtime must be downloaded manually on a trusted network and placed in src-tauri/webview2-fixed-runtime/ (see docs/build-webview2.md)."
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

Get-PinnedArtifact -Name 'ffmpeg' -Pin $pins.ffmpeg
foreach ($entry in $pins.models.PSObject.Properties) {
    Get-PinnedArtifact -Name $entry.Name -Pin $entry.Value
}

if ($UpdatePins) {
    $pins | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $PSScriptRoot 'pins.json') -Encoding utf8
    Write-Host "pins.json updated. Review and commit before the first real build."
}

Write-Host '[1/4] frontend'
Push-Location (Join-Path $root 'frontend')
try {
    npm ci
    npm run build
} finally { Pop-Location }

Write-Host '[2/4] python sidecar'
Push-Location (Join-Path $root 'backend')
try {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
    .\.venv\Scripts\pyinstaller.exe --noconfirm --clean packaging\sidecar.spec
} finally { Pop-Location }

Write-Host '[3/4] tauri shell'
Push-Location (Join-Path $root 'src-tauri')
try {
    cargo build --release
} finally { Pop-Location }

if ($SkipInstaller) {
    Write-Host '[4/4] skipped installer (-SkipInstaller)'
    exit 0
}

Write-Host '[4/4] nsis installer'
Push-Location (Join-Path $root 'src-tauri')
try {
    npx --yes @tauri-apps/cli@2 build --bundles nsis
} finally { Pop-Location }

$built = Get-ChildItem -Path (Join-Path $root 'src-tauri/target/release/bundle/nsis') -Filter '*.exe' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $built) { throw 'NSIS installer was not produced.' }

$final = Join-Path $delivery ("CuttingEdgeV2-Setup-v$version.exe")
Copy-Item $built.FullName $final -Force
$hash = (Get-FileHash $final -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$final.sha256" -Value "$hash  CuttingEdgeV2-Setup-v$version.exe" -Encoding ascii

$sizeGb = [math]::Round((Get-Item $final).Length / 1GB, 2)
Write-Host "`n[delivered] $final"
Write-Host "[size     ] $sizeGb GB (budget 3.5 GB)"
Write-Host "[sha256   ] $hash"
