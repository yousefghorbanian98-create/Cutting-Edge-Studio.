<#
Build-machine-only native probe. This is NOT installer/GUI/offline acceptance.
Downloads only the reviewed checksum-pinned LGPL shared archive from pins.json,
keeps all tools/media outside the checkout, and executes the actual Windows tools.
#>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputDir, [string]$CacheDir = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pin = (Get-Content (Join-Path $repo 'scripts/pins.json') -Raw | ConvertFrom-Json).ffmpeg
if ($pin.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Native probe requires a reviewed SHA-256 pin.' }
if ($pin.url -notmatch '^https://github\.com/BtbN/FFmpeg-Builds/releases/download/autobuild-[^/]+/ffmpeg-[^/]+-win64-lgpl-shared-9\.0\.zip$') {
    throw 'Refusing anything except the reviewed dated Windows LGPL shared asset.'
}
if (Test-Path $OutputDir) { throw 'Use a fresh disposable probe directory; existing content is preserved.' }
New-Item -ItemType Directory -Path $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
$archive = Join-Path $OutputDir 'ffmpeg.zip'
# A 76 MB fetch over the release CDN intermittently returns 504 for minutes at
# a time. Retry patiently rather than losing a 60-minute Windows build to an
# upstream outage; the checksum below is still the gate and an unverified
# archive never proceeds.
$downloaded = $false
$cached = ''
if ($CacheDir) { $cached = Join-Path $CacheDir 'ffmpeg.zip' }
# A cached copy is trusted only after it matches the reviewed hash, so a stale
# or tampered cache entry can never substitute for the pinned archive.
if ($cached -and (Test-Path $cached)) {
    if ((Get-FileHash $cached -Algorithm SHA256).Hash.ToLowerInvariant() -eq $pin.sha256) {
        Copy-Item $cached $archive
        $downloaded = $true
        Write-Host 'Reusing the cached pinned archive (checksum verified).'
    } else {
        Write-Host '::warning title=Pinned tool cache::cached archive failed its checksum; re-downloading.'
        Remove-Item $cached -Force
    }
}
if (-not $downloaded) { foreach ($attempt in 1..8) {
    try {
        Invoke-WebRequest -Uri $pin.url -OutFile $archive -UseBasicParsing
        $downloaded = $true
        break
    } catch {
        $lastError = $_.Exception.Message
        Write-Host "::warning title=Pinned tool download retry::attempt $attempt failed: $lastError"
        if (Test-Path $archive) { Remove-Item $archive -Force }
        if ($attempt -lt 8) { Start-Sleep -Seconds @(10, 20, 30, 45, 60, 60, 60)[$attempt - 1] }
    }
} }
if (-not $downloaded) {
    Write-Host "::error title=Pinned tool download failed::url=$($pin.url)%0Alast error: $lastError"
    throw "Could not download the pinned native-tool archive after 8 attempts: $lastError"
}
$actualHash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $pin.sha256) { throw 'Downloaded native-tool archive does not match its reviewed checksum.' }
if ($cached -and -not (Test-Path $cached)) {
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    Copy-Item $archive $cached -Force
}
$unpacked = Join-Path $OutputDir 'unpacked'
Expand-Archive -Path $archive -DestinationPath $unpacked
$executables = @(Get-ChildItem $unpacked -Recurse -Filter ffmpeg.exe)
if ($executables.Count -ne 1) { throw 'Expected exactly one ffmpeg.exe in the verified archive.' }
$ffmpeg = $executables[0].FullName
$bin = $executables[0].Directory.FullName
$ffprobe = Join-Path $bin 'ffprobe.exe'
if (-not (Test-Path $ffprobe)) { throw 'The verified archive has no matching ffprobe.exe.' }

function Invoke-NativeTool {
    param([string]$Executable, [string[]]$Arguments)
    $output = & $Executable @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Native tool failed (exit $LASTEXITCODE): $($output -join [Environment]::NewLine)"
    }
    return ($output -join [Environment]::NewLine)
}

$version = Invoke-NativeTool $ffmpeg @('-version')
$buildconf = Invoke-NativeTool $ffmpeg @('-buildconf')
$license = Invoke-NativeTool $ffmpeg @('-L')
$encoders = Invoke-NativeTool $ffmpeg @('-hide_banner', '-encoders')
$filters = Invoke-NativeTool $ffmpeg @('-hide_banner', '-filters')
if ($buildconf -notmatch '--enable-shared' -or $buildconf -match '--enable-(gpl|nonfree)(\s|$)') {
    throw 'Native build is not the required shared, non-GPL/nonfree configuration.'
}
if ($license -notmatch 'GNU Lesser General Public License') { throw 'Native tool did not report LGPL licensing.' }
if ($encoders -match '\blibx26[245]\b') { throw 'Forbidden GPL encoder is present.' }
if ($encoders -notmatch '\blibopenh264\b') { throw 'Required BSD openh264 encoder is absent; no prohibited fallback will be used.' }
$dlls = @(Get-ChildItem $bin -Filter 'avcodec-*.dll')
if ($dlls.Count -lt 1) { throw 'Expected a separate shared avcodec DLL.' }

$media = Join-Path $OutputDir 'owned-openh264.mp4'
$null = Invoke-NativeTool $ffmpeg @('-hide_banner', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i',
    'color=c=black:s=160x96:r=25:d=1', '-an', '-pix_fmt', 'yuv420p', '-c:v', 'libopenh264', $media)
$probeText = Invoke-NativeTool $ffprobe @('-v', 'error', '-show_format', '-show_streams', '-of', 'json', $media)
$probe = $probeText | ConvertFrom-Json
$video = @($probe.streams | Where-Object { $_.codec_type -eq 'video' })
if ($video.Count -ne 1 -or $video[0].codec_name -ne 'h264' -or $video[0].width -ne 160 -or $video[0].height -ne 96) {
    throw 'Encoded output failed the real ffprobe codec/dimensions check.'
}
if ([double]$probe.format.duration -lt 0.9 -or [double]$probe.format.duration -gt 1.2) { throw 'Encoded duration is outside the owned fixture bounds.' }
$null = Invoke-NativeTool $ffmpeg @('-hide_banner', '-nostdin', '-v', 'error', '-xerror', '-i', $media, '-f', 'null', '-')

# Feasibility check for a ready LGPL shot-candidate alternative, not TransNetV2.
$scdetAvailable = [bool]($filters -match '\bscdet\b')
$sceneProbe = $null
if (-not $scdetAvailable) { throw 'The pinned build lacks the required ready scdet filter; no scene result is fabricated.' }
if ($scdetAvailable) {
    $graph = 'color=c=black:s=160x96:r=25:d=1[black];color=c=white:s=160x96:r=25:d=1[white];[black][white]concat=n=2:v=1:a=0,scdet=threshold=10'
    $sceneText = Invoke-NativeTool $ffprobe @('-v', 'error', '-f', 'lavfi', '-i', $graph,
        '-show_frames', '-show_entries', 'frame=pts_time:frame_tags=lavfi.scd.score,lavfi.scd.time', '-of', 'json')
    $sceneProbe = $sceneText | ConvertFrom-Json
    $cuts = @($sceneProbe.frames | Where-Object { $_.tags -and $null -ne $_.tags.'lavfi.scd.time' })
    if ($cuts.Count -ne 1 -or [math]::Abs([double]$cuts[0].tags.'lavfi.scd.time' - 1.0) -gt 0.05) {
        throw 'Ready scdet filter failed the owned black-to-white single-cut fixture.'
    }
}

$record = [ordered]@{
    scope = 'windows-native-media-tools-only'
    source_revision = (& git -C $repo rev-parse HEAD).Trim()
    archive_url = $pin.url
    archive_sha256 = $actualHash
    version = $version
    build_configuration = $buildconf
    license_output = $license
    encoders = $encoders
    filters = $filters
    shared_avcodec_dlls = @($dlls.Name)
    media_sha256 = (Get-FileHash $media -Algorithm SHA256).Hash.ToLowerInvariant()
    measured_probe = $probe
    openh264_encode_and_decode = 'passed'
    scdet_available = $scdetAvailable
    scdet_owned_fixture = $sceneProbe
    limits = @('Build-machine download only.', 'Not a complete transitive-licence certificate.',
        'Not installed-app, GUI, packaged worker, offline, NVENC or performance acceptance.',
        'No generated media or native binaries are committed or bundled by this probe.')
}
$record | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $OutputDir 'probe.json') -Encoding utf8
Write-Output '::notice title=Windows native media tools::PASS: reviewed archive checksum; LGPL shared configuration; no forbidden encoders; real libopenh264 encode, ffprobe facts, error-checked decode and one native scdet candidate at 1 second. This is tools-only, not installer/runtime acceptance.'
