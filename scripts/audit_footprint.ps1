# scripts/audit_footprint.ps1 - Backward compatibility wrapper delegating to scripts/audit/audit_footprint.ps1
[CmdletBinding()]
param (
    [string]$Path = ""
)

$targetScript = Join-Path $PSScriptRoot "audit\audit_footprint.ps1"
if (Test-Path $targetScript) {
    if ($Path) {
        & $targetScript -Path $Path
    } else {
        & $targetScript
    }
} else {
    Write-Error "Audit footprint script not found at $targetScript"
}
