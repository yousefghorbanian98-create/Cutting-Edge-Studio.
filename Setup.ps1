# Cutting Edge Studio — Setup Entry (double-click)
# این فایل فقط launcher است — منطق اصلی در scripts/OneClick-Setup.ps1
param()
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$main = Join-Path $root "scripts\OneClick-Setup.ps1"
if (-not (Test-Path $main)) { Write-Error "OneClick-Setup.ps1 یافت نشد! هر دو Part را کنار هم Extract کرده‌اید؟"; pause; exit 1 }
# Request admin and launch GUI
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$main`"" -Verb RunAs
    exit 0
}
& $main
