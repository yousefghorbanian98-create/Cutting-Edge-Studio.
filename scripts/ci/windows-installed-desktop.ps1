<# Real NSIS installation + native shell launch + orderly process-tree exit.
   Light build only. Does not certify WebView pixels, offline models or abrupt shell death. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputDir, [switch]$AllowMachineCdpPolicy)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
$records = [System.Collections.Generic.List[object]]::new()
function Check([string]$Name, [bool]$Passed) {
    $records.Add(@{ name = $Name; passed = $Passed })
    Write-Host "[$Passed] $Name"
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
$edgeDiagnostics = @()
$policyPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments'
$policyWasPresent = $false
$policyBackups = [System.Collections.Generic.List[object]]::new()
$policyRestoreFailed = $false
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
    if ($AllowMachineCdpPolicy) {
        # Runtime >=150 ignores env/HKCU overrides for elevated Windows runners.
        # Microsoft-supported, app-specific HKLM test policy; never modify product code.
        # https://github.com/MicrosoftEdge/WebView2Feedback/issues/5645
        Check 'machine CDP policy restricted to disposable GitHub Windows runner' ($env:GITHUB_ACTIONS -eq 'true' -and $env:RUNNER_OS -eq 'Windows')
        $policyWasPresent = Test-Path $policyPath
        if (-not $policyWasPresent) { New-Item -Path $policyPath -Force | Out-Null }
        $policy = Get-Item $policyPath
        $appId = (Get-Content src-tauri/tauri.conf.json -Raw | ConvertFrom-Json).identifier
        foreach ($name in @($appId, (Split-Path $shell -Leaf))) {
            $exists = $policy.GetValueNames() -contains $name
            $backup = @{ name = $name; existed = $exists }
            if ($exists) {
                $backup.value = $policy.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                $backup.kind = $policy.GetValueKind($name).ToString()
            }
            $policyBackups.Add($backup)
            New-ItemProperty -Path $policyPath -Name $name -Value '--remote-debugging-port=9222' -PropertyType String -Force | Out-Null
        }
        $policy.Close()
        # No wildcard or user-scoped policy; remove env override so HKLM is selected.
        $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $null
    }
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
    $edgeDiagnostics = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedgewebview2.exe' } | ForEach-Object {
        @{ pid = $_.ProcessId; parent = $_.ParentProcessId; debug_flag = [bool]($_.CommandLine -match '--remote-debugging-port=9222') }
    })
    Write-Output "::notice title=Native WebView debug diagnostics::$($edgeDiagnostics | ConvertTo-Json -Compress)"
    & node scripts/ci/windows-webview-smoke.cjs $OutputDir
    $uiPassed = $LASTEXITCODE -eq 0
    $records.Add(@{ name = 'actual installed WebView DOM and screenshot verified'; passed = $uiPassed })
    if (-not $uiPassed) { Write-Output '::error title=Installed WebView gate::Native DOM/screenshot gate failed; orderly cleanup is still tested independently.' }
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
    if (-not $uiPassed) { throw 'Actual installed WebView DOM/screenshot gate failed; see webview.json.' }
} catch {
    $detail = $_.Exception.Message.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Output "::error title=Installed desktop execution::$detail"
    throw
} finally {
    if ($native -and -not $native.HasExited) {
        & taskkill /PID $native.Id /T /F
        Write-Host "Emergency harness cleanup exit: $LASTEXITCODE (not runtime containment proof)"
    }
    foreach ($backup in $policyBackups) {
        try {
            if ($backup.existed) {
                New-ItemProperty -Path $policyPath -Name $backup.name -Value $backup.value -PropertyType $backup.kind -Force | Out-Null
            } else { Remove-ItemProperty -Path $policyPath -Name $backup.name -ErrorAction Stop }
        } catch {
            $policyRestoreFailed = $true
            Write-Output "::error title=Test policy cleanup::Failed to restore app-specific machine CDP policy: $($_.Exception.GetType().Name)"
        }
    }
    if ($policyBackups.Count -gt 0 -and -not $policyWasPresent -and -not $policyRestoreFailed) {
        try {
            $key = Get-Item $policyPath
            $empty = $key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0
            $key.Close()
            if ($empty) { Remove-Item $policyPath -ErrorAction Stop }
        } catch {
            $policyRestoreFailed = $true
            Write-Output "::error title=Test policy cleanup::Failed to remove empty test policy key: $($_.Exception.GetType().Name)"
        }
    }
    $env:CUTTING_EDGE_DATA_DIR = $oldData
    $env:CUTTING_EDGE_HOME = $oldHome
    $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $oldWebViewArgs
    $env:NODE_PATH = $oldNodePath
    $log = Join-Path $data 'logs/backend.jsonl'
    if (Test-Path $log) { Copy-Item $log (Join-Path $OutputDir 'backend.jsonl') -Force }
    $report = @{ checks = $records.ToArray(); paths = $pathEvidence; browser_processes = $edgeDiagnostics; limitations = @('Light installer only; pretrained artifacts and fixed WebView runtime are absent.', 'Native WebView DOM/CDP screenshot gate is separate from full media/render quality acceptance.', 'Orderly close only; abrupt shell-death OS containment remains OPEN.'); install = $install; test_only_cdp_policy = @{ app_ids = @($policyBackups | ForEach-Object { $_.name }); restored = -not $policyRestoreFailed } }
    $report | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputDir 'installed.json') -Encoding utf8
    # One bounded summary avoids GitHub's per-step annotation quota.
    Write-Output "::notice title=Installed desktop summary::$($report | ConvertTo-Json -Depth 8 -Compress)"
    $uninstaller = Join-Path $install 'uninstall.exe'
    if (Test-Path $uninstaller) {
        $uninstall = Start-Process $uninstaller -ArgumentList '/S' -PassThru -Wait
        Write-Host "NSIS cleanup exit: $($uninstall.ExitCode)"
    }
    if ($policyRestoreFailed) { throw 'App-specific CI CDP policy restoration failed.' }
}
