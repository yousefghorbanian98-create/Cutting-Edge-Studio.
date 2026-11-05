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
    Write-Output "::notice title=Installed desktop acceptance::$Passed : $Name"
    if (-not $Passed) {
        Write-Output "::error title=Installed desktop acceptance::$Name"
        throw "Installed desktop gate failed: $Name"
    }
}
function Same-LocalPath([string]$Left, [string]$Right) {
    # TEMP may use RUNNER~1 while GetModuleFileName/resource_dir uses the long
    # name. Compare Windows file identity, NOT unequal string spellings or extended-path prefixes.
    $same = & python -c 'import os, sys; print(os.path.samefile(sys.argv[1], sys.argv[2]))' $Left $Right
    if ($LASTEXITCODE -ne 0) { throw 'Canonical path comparison failed.' }
    Write-Host "path identity: $Left <=> $Right : $same"
    return "$same".Trim() -eq 'True'
}
$pathEvidence = @{}
$install = Join-Path $env:TEMP 'CE installed smoke نصب با فاصله'
$data = Join-Path $env:TEMP ('ce-installed-data-' + [guid]::NewGuid().ToString('N'))
$native = $null
$installer = Get-ChildItem delivery -Filter 'CuttingEdgeV2-Setup-*.exe' | Select-Object -First 1
$oldData = $env:CUTTING_EDGE_DATA_DIR
$oldHome = $env:CUTTING_EDGE_HOME
$oldWebViewArgs = $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
$oldNodePath = $env:NODE_PATH
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
    Check 'test-only CDP port initially unused' (-not (Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue))
    # Test process only: installed binaries/config do not ship this debugging flag.
    $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222'
    $env:NODE_PATH = Join-Path $env:RUNNER_TEMP 'ce-webview-tools/node_modules'
    $native = Start-Process $shell -WorkingDirectory $env:TEMP -PassThru
    $deadline = (Get-Date).AddSeconds(75)
    $health = $null
    do {
        if ($native.HasExited) { throw "Installed native shell exited before startup: $($native.ExitCode)" }
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8756/api/v1/health' -TimeoutSec 2 -NoProxy }
        catch { Write-Host "Waiting for installed backend: $($_.Exception.Message)"; Start-Sleep -Milliseconds 250 }
    } while (-not $health -and (Get-Date) -lt $deadline)
    Check 'native shell launched healthy sidecar without Vite' ($health.status -eq 'ok')
    $pathEvidence = @{ expected_models = (Join-Path $install 'models'); observed_models = $health.models_dir; expected_database = (Join-Path $data 'cutting-edge.db'); observed_database = $health.database }
    Write-Output "::notice title=Installed native paths::$($pathEvidence | ConvertTo-Json -Compress)"
    # models/ may be absent in a light bundle: compare its existing install
    # parent by Windows file identity, including extended \\?\ and 8.3 aliases.
    Check 'native resource_dir overrides inherited home' (((Split-Path $health.models_dir -Leaf) -eq 'models') -and (Same-LocalPath (Split-Path $health.models_dir -Parent) $install))
    Check 'profile is separate from installation' (Same-LocalPath $health.database (Join-Path $data 'cutting-edge.db'))
    $page = Invoke-WebRequest 'http://127.0.0.1:8756/' -NoProxy
    Check 'installed same-origin built React is served' ($page.StatusCode -eq 200 -and $page.Content.Contains('type="module"'))
    $native.Refresh()
    Check 'native window is present' ($native.MainWindowHandle -ne 0)
    & node scripts/ci/windows-webview-smoke.cjs $OutputDir
    Check 'actual installed WebView DOM and screenshot verified' ($LASTEXITCODE -eq 0)
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
} catch {
    $detail = $_.Exception.Message.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Output "::error title=Installed desktop execution::$detail"
    throw
} finally {
    if ($native -and -not $native.HasExited) {
        & taskkill /PID $native.Id /T /F
        Write-Host "Emergency harness cleanup exit: $LASTEXITCODE (not runtime containment proof)"
    }
    $env:CUTTING_EDGE_DATA_DIR = $oldData
    $env:CUTTING_EDGE_HOME = $oldHome
    $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $oldWebViewArgs
    $env:NODE_PATH = $oldNodePath
    $log = Join-Path $data 'logs/backend.jsonl'
    if (Test-Path $log) { Copy-Item $log (Join-Path $OutputDir 'backend.jsonl') -Force }
    @{ checks = $records.ToArray(); paths = $pathEvidence; limitations = @('Light installer only; pretrained artifacts and fixed WebView runtime are absent.', 'Native WebView DOM/CDP screenshot gate is separate from full media/render quality acceptance.', 'Orderly close only; abrupt shell-death OS containment remains OPEN.'); install = $install } |
        ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputDir 'installed.json') -Encoding utf8
    $uninstaller = Join-Path $install 'uninstall.exe'
    if (Test-Path $uninstaller) {
        $uninstall = Start-Process $uninstaller -ArgumentList '/S' -PassThru -Wait
        Write-Host "NSIS cleanup exit: $($uninstall.ExitCode)"
    }
}
