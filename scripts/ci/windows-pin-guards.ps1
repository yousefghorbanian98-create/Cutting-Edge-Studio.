<# Negative contract tests of the real build function; no downloads, no fake artifacts.
   Reuse PowerShell's AST, not a copied implementation/custom PowerShell parser. #>
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$source = [System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path scripts/build-installer.ps1).Path, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | Out-String) }
$definition = $source.Find({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-PinnedArtifact'
}, $true)
if (-not $definition) { throw 'Real Get-PinnedArtifact definition missing.' }
. ([scriptblock]::Create($definition.Extent.Text))
$root = Join-Path $env:TEMP ('ce-pin-negative-' + [guid]::NewGuid().ToString('N'))
$UpdatePins = $false
$PSDefaultParameterValues['Invoke-WebRequest:TimeoutSec'] = 1
$cases = @(
    @{ pin = @{ url = 'https://invalid.invalid/guard.zip'; sha256 = $null; target = 'uncreated' }; error = 'Invalid SHA-256 pin*' },
    @{ pin = @{ url = 'https://invalid.invalid/guard.zip'; sha256 = 'not-a-sha256'; target = 'uncreated' }; error = 'Invalid SHA-256 pin*' },
    @{ pin = @{ url = 'https://invalid.invalid/guard.zip'; sha256 = ('a' * 64); target = $null }; error = 'Missing artifact target*' }
)
foreach ($case in $cases) {
    $rejected = $false
    try { Get-PinnedArtifact -Name 'negative-contract' -Pin ([pscustomobject]$case.pin) }
    catch {
        if ($_.Exception.Message -notlike $case.error) { throw }
        Write-Host "Expected build rejection: $($_.Exception.Message)"
        $rejected = $true
    }
    if (-not $rejected -or (Test-Path $root)) { throw 'Invalid pin was not rejected before target creation.' }
}
Write-Output '::notice title=Artifact pin guard contract::PASS: null hash, malformed hash and missing target fail before target creation/network code.'
