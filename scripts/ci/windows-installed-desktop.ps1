<# Real NSIS installation + native shell launch + orderly process-tree exit.
   Light build only. Does not certify WebView pixels, offline models or abrupt shell death. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
$records = [System.Collections.Generic.List[object]]::new()
function Check([string]$Name, [bool]$Passed) {
    $records.Add(@{ name = $Name; passed = $Passed })
    Write-Host "[$Passed] $Name"
    if (-not $Passed) { throw "Installed desktop gate failed: $Name" }
}
$install = Join-Path $env:TEMP 'CE installed smoke نصب با فاصله'
$data = Join-Path $env:TEMP ('ce-installed-data-' + [guid]::NewGuid().ToString('N'))
$native = $null
$installer = Get-ChildItem delivery -Filter 'CuttingEdgeV2-Setup-*.exe' | Select-Object -First 1
$oldData = $env:CUTTING_EDGE_DATA_DIR
$oldHome = $env:CUTTING_EDGE_HOME
try {
    Check 'fixed desktop port initially unused' (-not (Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue))
    Check 'installer artifact exists' ($null -ne $installer)
    $setup = Start-Process $installer.FullName -ArgumentList "/S /D=$install" -PassThru -Wait
    Check 'NSIS silent install succeeded' ($setup.ExitCode -eq 0)
    $shell = Join-Path $install 'cutting-edge-v2.exe'
    Check 'installed native shell exists' (Test-Path $shell)
    Check 'onedir dependency resources installed' (Test-Path (Join-Path $install '_internal/python311.dll'))
    Check 'built UI resources installed' (Test-Path (Join-Path $install 'frontend/index.html'))
    Check 'light bundle mode explicitly recorded' ((Get-Content (Join-Path $install 'bundle-status.json') -Raw | ConvertFrom-Json).mode -eq 'light')
    $env:CUTTING_EDGE_DATA_DIR = $data
    # Deliberately wrong inherited home: native resolver must replace this with resource_dir.
    $env:CUTTING_EDGE_HOME = Join-Path $env:TEMP 'wrong inherited resource directory'
    $native = Start-Process $shell -WorkingDirectory $env:TEMP -PassThru
    $deadline = (Get-Date).AddSeconds(75)
    $health = $null
    do {
        if ($native.HasExited) { throw "Installed native shell exited before startup: $($native.ExitCode)" }
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8756/api/v1/health' -TimeoutSec 2 -NoProxy }
        catch { Write-Host "Waiting for installed backend: $($_.Exception.Message)"; Start-Sleep -Milliseconds 250 }
    } while (-not $health -and (Get-Date) -lt $deadline)
    Check 'native shell launched healthy sidecar without Vite' ($health.status -eq 'ok')
    Check 'native resource_dir overrides inherited home' ($health.models_dir -eq (Join-Path $install 'models'))
    Check 'profile is separate from installation' ($health.database -eq (Join-Path $data 'cutting-edge.db'))
    $page = Invoke-WebRequest 'http://127.0.0.1:8756/' -NoProxy
    Check 'installed same-origin built React is served' ($page.StatusCode -eq 200 -and $page.Content.Contains('type="module"'))
    $native.Refresh()
    Check 'native window is present' ($native.MainWindowHandle -ne 0)
    # Record backend descendants of this shell only; no unrelated process inspection in evidence.
    $all = @(Get-CimInstance Win32_Process)
    $parents = @($native.Id)
    $descendants = @()
    do {
        $children = @($all | Where-Object { $_.ParentProcessId -in $parents })
        $descendants += $children
        $parents = @($children | ForEach-Object { $_.ProcessId })
    } while ($parents.Count -gt 0)
    $backends = @($descendants | Where-Object { $_.Name -eq 'cutting-edge-backend.exe' })
    Check 'owned installed backend process captured' ($backends.Count -ge 1)
    $backends | Select-Object ProcessId, ParentProcessId, Name, CreationDate | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutputDir 'owned-processes.json') -Encoding utf8
    Check 'native window accepts orderly close' ($native.CloseMainWindow())
    Check 'native shell exits within 20 seconds' ($native.WaitForExit(20000))
    $deadline = (Get-Date).AddSeconds(10)
    do {
        $remaining = @($backends | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue })
        if ($remaining.Count -gt 0) { Start-Sleep -Milliseconds 100 }
    } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)
    Check 'owned backend gone after orderly native exit' ($remaining.Count -eq 0)
    Check 'desktop listening port released' (-not (Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue))
} finally {
    if ($native -and -not $native.HasExited) {
        & taskkill /PID $native.Id /T /F
        Write-Host "Emergency harness cleanup exit: $LASTEXITCODE (not runtime containment proof)"
    }
    $env:CUTTING_EDGE_DATA_DIR = $oldData
    $env:CUTTING_EDGE_HOME = $oldHome
    $log = Join-Path $data 'logs/backend.jsonl'
    if (Test-Path $log) { Copy-Item $log (Join-Path $OutputDir 'backend.jsonl') -Force }
    @{ checks = @($records); limitations = @('Light installer only; pretrained artifacts and fixed WebView runtime are absent.', 'HTTP + native window presence is not a WebView pixel/render assertion.', 'Orderly close only; abrupt shell-death OS containment remains OPEN.'); install = $install } |
        ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputDir 'installed.json') -Encoding utf8
    $uninstaller = Join-Path $install 'uninstall.exe'
    if (Test-Path $uninstaller) {
        $uninstall = Start-Process $uninstaller -ArgumentList '/S' -PassThru -Wait
        Write-Host "NSIS cleanup exit: $($uninstall.ExitCode)"
    }
}
