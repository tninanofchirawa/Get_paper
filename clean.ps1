# clean.ps1 - Root convenience launcher delegating to scripts/maintenance/clean.ps1
[CmdletBinding()]
param (
    [switch]$DryRun
)

$targetScript = Join-Path $PSScriptRoot "scripts\maintenance\clean.ps1"
if (Test-Path $targetScript) {
    if ($DryRun) {
        & $targetScript -DryRun
    } else {
        & $targetScript
    }
} else {
    Write-Error "Maintenance clean script not found at $targetScript"
}
