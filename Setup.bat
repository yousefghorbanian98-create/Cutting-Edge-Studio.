@echo off
:: Cutting Edge Studio — One-Click Setup Launcher (Game-like)
:: 2 پارت را کنار هم Extract کنید، فقط این فایل را به عنوان Administrator اجرا کنید
title Cutting Edge Studio Setup
echo ============================================
echo  Cutting Edge Studio v1.0.0 — One-Click Setup
echo  Double-click as Administrator to start
echo ============================================
:: Check for PowerShell 7 (pwsh) or fallback to Windows PowerShell
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -ExecutionPolicy Bypass -File "%~dp0scripts\OneClick-Setup.ps1" %*
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0scripts\OneClick-Setup.ps1" %*
)
if %ERRORLEVEL% neq 0 (
    echo Setup failed — see log in %TEMP%\CuttingEdge-Setup-*.log
    pause
)
