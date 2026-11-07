#Requires -Version 5.1
<#
.SYNOPSIS
    GitHub 2GB Splitter — Cutting Edge Studio Full Package
    هر فایل بالای 2GB را به 2+ تکه برای آپلود گیت‌هاب تقسیم می‌کند (مثل نصب بازی‌ها)

.DESCRIPTION
    مشکل: GitHub Release هر فایل را max 2GB می‌پذیرد، ولی Full Installer ما ~3.5GB است.
    راه‌حل بازی‌ها: یک نصب‌کننده کوچک + چند Data.bin کنار هم.

    این اسکریپت بعد از ساخت Full Installer به صورت اتوماتیک:
      1. حجم را چک می‌کند — اگر >1900MB بود به 2 تکه 1750MB تقسیم می‌کند (7z split)
      2. اگر <2GB بود فقط یک هش می‌سازد
      3. یک اسکریپت JOIN.bat + JOIN.sh می‌سازد تا کاربر با یک کلیک دوباره به هم بچسباند

    استفاده:
      pwsh -File scripts/split-for-github.ps1 -File delivery/CuttingEdgeV2-Setup-v1.0.0.exe
      pwsh -File scripts/split-for-github.ps1 -File delivery/CuttingEdge-Studio-v1.0.0-FULL.zip -ChunkMB 9  # برای دموی فعلی

    روی لینوکس همین منطق با: split -b 1900M یا zip -s 1900m
#>
param(
    [Parameter(Mandatory=$true)][string]$File,
    [int]$ChunkMB = 1900,  # GitHub safe: 1900MB < 2GB
    [switch]$Demo9MB       # برای دموی فعلی 18MB -> 2 تکه 9MB
)

if ($Demo9MB) { $ChunkMB = 9 }

if (-not (Test-Path $File)) { throw "فایل یافت نشد: $File" }

$sizeMB = [math]::Round((Get-Item $File).Length / 1MB, 1)
$sizeGB = [math]::Round($sizeMB / 1024, 2)
Write-Host "File: $File — $sizeMB MB ($sizeGB GB) — Limit: $ChunkMB MB"

if ($sizeMB -le $ChunkMB) {
    Write-Host "✓ زیر سقف گیت‌هاب — نیازی به تقسیم نیست"
    $hash = (Get-FileHash $File -Algorithm SHA256).Hash
    $hash | Out-File "$File.sha256" -Encoding ascii
    Write-Host "SHA256: $hash"
    Write-Host "آماده آپلود به GitHub Release: gh release upload v1.0.0 $File"
    return
}

# Needs split — مثل بازی: 7z split یا zip split
$base = [System.IO.Path]::GetFileNameWithoutExtension($File)
$ext = [System.IO.Path]::GetExtension($File)
$dir = Split-Path $File -Parent
if (-not $dir) { $dir = "." }

# Check if 7z available (best for game-like)
$has7z = Get-Command 7z -ErrorAction SilentlyContinue
if ($has7z) {
    Write-Host "تقسیم با 7z به تکه‌های ${ChunkMB}MB..."
    $out = Join-Path $dir "$base.7z"
    # 7z a -v1900m = split archive
    & 7z a -t7z -mx=9 -m0=lzma2 -ms=on -v"$($ChunkMB)m" "$out" "$File" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "7z split failed" }
    $parts = Get-ChildItem "$out.*"
    Write-Host "ساخته شد $($parts.Count) تکه:"
    $parts | ForEach-Object { Write-Host "  $($_.Name) — $([math]::Round($_.Length/1MB,1)) MB" }
} else {
    # Fallback: PowerShell split
    Write-Host "7z یافت نشد — با PowerShell split به $ChunkMB MB..."
    $chunkBytes = $ChunkMB * 1024 * 1024
    $in = [System.IO.File]::OpenRead($File)
    $partNum = 1
    $buffer = New-Object byte[] $chunkBytes
    $parts = @()
    while (($read = $in.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $partName = "$File.part$($partNum.ToString('000'))"
        $out = [System.IO.File]::Create($partName)
        $out.Write($buffer, 0, $read)
        $out.Close()
        $parts += $partName
        Write-Host "  $partName — $([math]::Round($read/1MB,1)) MB"
        $partNum++
    }
    $in.Close()
}

# Create JOIN scripts (exactly like game repacks)
$joinBat = @"
@echo off
echo Joining GitHub parts for $base$ext ...
copy /b "$base$ext.part001" + "$base$ext.part002" "$base$ext"
echo Verifying SHA256...
certutil -hashfile "$base$ext" SHA256
pause
"@
$joinSh = @"
#!/bin/bash
# Join GitHub parts on Linux/macOS
cat "$base$ext.part"* > "$base$ext"
sha256sum "$base$ext"
"@

$joinBat | Out-File (Join-Path $dir "JOIN-$base.bat") -Encoding ascii
$joinSh | Out-File (Join-Path $dir "JOIN-$base.sh") -Encoding ascii

Write-Host "`n=== آماده آپلود به گیت‌هاب ==="
Write-Host "هر تکه <2GB است — الان می‌توانی:"
Write-Host "  gh release upload v1.0.0 $File.part*"
Write-Host "کاربر دانلود می‌کند هر دو پارت را در یک پوشه + JOIN.bat را یک کلیک می‌زند → $base$ext کامل 3.5GB ساخته می‌شود"

# Also create README for this delivery
@"
# GitHub 2GB Split — $base$ext
حجم اصلی: $sizeMB MB (سقف گیت‌هاب 2000MB)
تکه‌ها: $($parts.Count) × ${ChunkMB}MB
ساخت: $(Get-Date -Format "yyyy-MM-dd HH:mm")
هش‌ها در .sha256
"@ | Out-File (Join-Path $dir "README-GitHub-Split.txt") -Encoding utf8
