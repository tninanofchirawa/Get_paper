# scripts/audit/audit_footprint.ps1 - Automated Project Footprint & Disk Usage Audit Utility
[CmdletBinding()]
param (
    [string]$Path = ""
)

$root = if ($Path) { (Resolve-Path $Path).Path } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "📊 PROJECT FOOTPRINT & DISK AUDIT: The_Paper_Getter" -ForegroundColor Cyan
Write-Host "📂 Root Path: $root" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$allFiles = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue
$totalBytes = ($allFiles | Measure-Object -Property Length -Sum).Sum
$totalMB = [Math]::Round($totalBytes / 1MB, 2)

# Top 10 Directories
Write-Host "`n📁 TOP 10 LARGEST DIRECTORIES (Ranked by MB):" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------"
Write-Host ("{0,-6} {1,-32} {2,12}" -f "Rank", "Directory Name", "Size (MB)")
Write-Host "-------------------------------------------------------"

$topLevelDirs = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue
$dirStats = foreach ($d in $topLevelDirs) {
    $dirFiles = Get-ChildItem -Path $d.FullName -Recurse -File -ErrorAction SilentlyContinue
    $dBytes = ($dirFiles | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{
        Name = $d.Name
        Bytes = if ($dBytes) { $dBytes } else { 0 }
        MB = [Math]::Round(($dBytes / 1MB), 2)
    }
}
$rank = 1
$dirStats | Sort-Object -Property Bytes -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host ("{0,-6} {1,-32} {2,12:N2} MB" -f $rank, $_.Name, $_.MB)
    $rank++
}
Write-Host "-------------------------------------------------------"

# Top 10 Files
Write-Host "`n📄 TOP 10 LARGEST INDIVIDUAL FILES (Ranked by MB):" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------------------------------"
Write-Host ("{0,-6} {1,-56} {2,14}" -f "Rank", "Relative Path", "Size (MB)")
Write-Host "--------------------------------------------------------------------------------"
$fRank = 1
$allFiles | Sort-Object -Property Length -Descending | Select-Object -First 10 | ForEach-Object {
    $rel = $_.FullName.Replace($root, "").TrimStart("\/")
    $disp = if ($rel.Length -le 55) { $rel } else { "..." + $rel.Substring($rel.Length - 52) }
    $fMB = [Math]::Round($_.Length / 1MB, 3)
    Write-Host ("{0,-6} {1,-56} {2,14:N3} MB" -f $fRank, $disp, $fMB)
    $fRank++
}
Write-Host "--------------------------------------------------------------------------------"

Write-Host "`n📦 TOTAL PROJECT DISK USAGE: $totalMB MB ($($allFiles.Count) total files)" -ForegroundColor Green
Write-Host "================================================================================`n" -ForegroundColor Cyan
