# scripts/audit_footprint.ps1 - Native PowerShell Project Footprint & Disk Usage Audit
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "📊 PROJECT FOOTPRINT & DISK AUDIT (PowerShell Scanner)" -ForegroundColor Cyan
Write-Host "📂 Workspace Root: $PSScriptRoot\.." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$rootDir = Resolve-Path "$PSScriptRoot\.."

# Top 10 Directories
Write-Host "`n📁 TOP 10 LARGEST DIRECTORIES (Ranked by MB):" -ForegroundColor Yellow
Write-Host ("-" * 55)
Write-Host ("{0,-6} {1,-32} {2,12}" -f "Rank", "Directory Name", "Size (MB)")
Write-Host ("-" * 55)

$dirs = Get-ChildItem -Path $rootDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $bytes = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{
        Name = $_.Name
        SizeMB = [math]::Round(($bytes / 1MB), 2)
    }
} | Sort-Object SizeMB -Descending

$rank = 1
foreach ($d in $dirs | Select-Object -First 10) {
    Write-Host ("{0,-6} {1,-32} {2,12:N2} MB" -f $rank, $d.Name, $d.SizeMB)
    $rank++
}
Write-Host ("-" * 55)

# Top 10 Individual Files
Write-Host "`n📄 TOP 10 LARGEST INDIVIDUAL FILES (Ranked by MB):" -ForegroundColor Yellow
Write-Host ("-" * 80)
Write-Host ("{0,-6} {1,-56} {2,14}" -f "Rank", "File Path", "Size (MB)")
Write-Host ("-" * 80)

$files = Get-ChildItem -Path $rootDir -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    [PSCustomObject]@{
        RelPath = $_.FullName.Replace($rootDir.Path + "\", "")
        SizeMB = [math]::Round(($_.Length / 1MB), 3)
    }
} | Sort-Object SizeMB -Descending

$fRank = 1
foreach ($f in $files | Select-Object -First 10) {
    $p = if ($f.RelPath.Length -gt 55) { "..." + $f.RelPath.Substring($f.RelPath.Length - 52) } else { $f.RelPath }
    Write-Host ("{0,-6} {1,-56} {2,14:N3} MB" -f $fRank, $p, $f.SizeMB)
    $fRank++
}
Write-Host ("-" * 80)

# Culprit Breakdown
Write-Host "`n🔍 COMMON DISK SPACE CULPRITS BREAKDOWN:" -ForegroundColor Yellow
Write-Host ("-" * 65)
Write-Host ("{0,-48} {1,14}" -f "Culprit Category", "Size (MB)")
Write-Host ("-" * 65)

function Measure-PatternSize($filterPattern) {
    $bytes = (Get-ChildItem -Path $rootDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match $filterPattern } | Measure-Object -Property Length -Sum).Sum
    return [math]::Round(($bytes / 1MB), 2)
}

$venvSize = Measure-PatternSize "\\.venv|\\venv"
$pycacheSize = Measure-PatternSize "\\__pycache__|\\.py[co]$"
$gitSize = Measure-PatternSize "\\.git"
$cacheSize = Measure-PatternSize "\\cache\\.*\.json$"
$dbSize = Measure-PatternSize "\.(db|sqlite|db-wal)$"
$outSize = Measure-PatternSize "\\output\\.*\.(csv|xlsx)$"

Write-Host ("{0,-48} {1,14:N2} MB" -f "Virtual Environment (.venv/ / venv/)", $venvSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "Python Bytecode (__pycache__ / *.pyc)", $pycacheSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "Git Storage (.git/objects/)", $gitSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "Cache Directory (cache/*.json)", $cacheSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "SQLite Databases (*.db / *.sqlite)", $dbSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "Exported Spreadsheets (output/*.csv / *.xlsx)", $outSize)
Write-Host ("-" * 65)

$totalBytes = (Get-ChildItem -Path $rootDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$totalMB = [math]::Round(($totalBytes / 1MB), 2)
$coreSourceMB = [math]::Round(($totalMB - $venvSize - $gitSize), 2)

Write-Host ("{0,-48} {1,14:N2} MB" -f "TOTAL ENTIRE WORKSPACE (including .venv)", $totalMB)
Write-Host ("{0,-48} {1,14:N2} MB" -f "VIRTUAL ENVIRONMENT (.venv)", $venvSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "GIT VERSION CONTROL REPOSITORY (.git)", $gitSize)
Write-Host ("{0,-48} {1,14:N2} MB" -f "CORE PROJECT SOURCE CODE & ASSETS", $coreSourceMB)
Write-Host ("=" * 80)

if ($coreSourceMB -lt 15.0) {
    Write-Host "✅ [SUCCESS] Lean Footprint Goal Met: Core project source is $coreSourceMB MB (< 15 MB threshold)!" -ForegroundColor Green
} else {
    Write-Host "⚠️ [NOTE] Core project source footprint is $coreSourceMB MB. Run clean.ps1 to purge caches." -ForegroundColor Yellow
}
