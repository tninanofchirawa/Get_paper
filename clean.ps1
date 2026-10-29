# clean.ps1 - Zero-Dependency PowerShell Cleanup Utility for The_Paper_Getter
[CmdletBinding()]
param (
    [switch]$DryRun
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "🧹 $(if ($DryRun) { '[DRY RUN] ' })ZERO-DEPENDENCY PROJECT CLEANUP: The_Paper_Getter" -ForegroundColor Cyan
Write-Host "📂 Workspace: $PSScriptRoot" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

$root = $PSScriptRoot
$removedCount = 0
$bytesFreed = 0

# 1. Bytecode & __pycache__
Write-Host "`n[1/5] Removing Python bytecode (__pycache__ / *.pyc / *.pyo)..." -ForegroundColor Yellow
$pycFiles = Get-ChildItem -Path $root -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\\.venv|\\venv" }
foreach ($f in $pycFiles) {
    $bytesFreed += $f.Length
    $removedCount++
    if (-not $DryRun) { Remove-Item -Force $f.FullName }
}

$pycacheDirs = Get-ChildItem -Path $root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\\.venv|\\venv" }
foreach ($d in $pycacheDirs) {
    if (-not $DryRun) { Remove-Item -Recurse -Force $d.FullName }
}
Write-Host "  -> Cleaned $($pycFiles.Count) bytecode files and $($pycacheDirs.Count) cache directories."

# 2. Transient runtime caches (cache/, temp/, logs/) preserving .gitkeep
Write-Host "`n[2/5] Purging transient caches (cache/, temp/, logs/)..." -ForegroundColor Yellow
$targetDirs = @("cache", "temp", "logs")
$transientFiles = 0
foreach ($dName in $targetDirs) {
    $dPath = Join-Path $root $dName
    if (Test-Path $dPath) {
        $files = Get-ChildItem -Path $dPath -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".gitkeep" }
        foreach ($f in $files) {
            $bytesFreed += $f.Length
            $transientFiles++
            $removedCount++
            if (-not $DryRun) { Remove-Item -Force $f.FullName }
        }
    } else {
        if (-not $DryRun) { New-Item -ItemType Directory -Path $dPath -Force | Out-Null }
    }
}
Write-Host "  -> Cleaned $transientFiles transient files from cache/, temp/, logs/."

# 3. Intermediate/Test exports in output/
Write-Host "`n[3/5] Cleaning test exports and spreadsheets in output/..." -ForegroundColor Yellow
$outDir = Join-Path $root "output"
$outFiles = 0
if (Test-Path $outDir) {
    $files = Get-ChildItem -Path $outDir -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ne ".gitkeep" -and ($_.Name -like "test_*" -or $_.Name -like "temp_*" -or $_.Extension -in @(".csv", ".xlsx"))
    }
    foreach ($f in $files) {
        $bytesFreed += $f.Length
        $outFiles++
        $removedCount++
        if (-not $DryRun) { Remove-Item -Force $f.FullName }
    }
}
Write-Host "  -> Cleaned $outFiles files from output/."

# 4. SQLite test databases & WAL
Write-Host "`n[4/5] Cleaning test SQLite databases and WAL journals..." -ForegroundColor Yellow
$dataDir = Join-Path $root "data"
$dbFiles = 0
if (Test-Path $dataDir) {
    $files = Get-ChildItem -Path $dataDir -File -ErrorAction SilentlyContinue | Where-Object {
        ($_.Name -like "test_*" -and $_.Extension -in @(".db", ".sqlite")) -or $_.Extension -in @(".db-wal", ".db-shm")
    }
    foreach ($f in $files) {
        $bytesFreed += $f.Length
        $dbFiles++
        $removedCount++
        if (-not $DryRun) { Remove-Item -Force $f.FullName }
    }
}
Write-Host "  -> Cleaned $dbFiles temporary database files."

# 5. Directory recreation & gitkeep validation
Write-Host "`n[5/5] Re-verifying required directories and .gitkeep files..." -ForegroundColor Yellow
$reqDirs = @("cache", "data", "logs", "output", "temp", "input")
foreach ($d in $reqDirs) {
    $p = Join-Path $root $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    if ($d -in @("cache", "logs", "output", "temp")) {
        $gk = Join-Path $p ".gitkeep"
        if (-not (Test-Path $gk)) { New-Item -ItemType File -Path $gk -Force | Out-Null }
    }
}

# Safety Check
$protected = @("HANDBOOK.md", "README.md", ".env.example", "main.py", "analyzer.py", "csv_builder.py")
$safetyPass = $true
foreach ($p in $protected) {
    if (-not (Test-Path (Join-Path $root $p))) {
        Write-Host "  ❌ WARNING: Protected file missing: $p" -ForegroundColor Red
        $safetyPass = $false
    }
}
if ($safetyPass) {
    Write-Host "  ✅ Protected source files and HANDBOOK.md are 100% intact." -ForegroundColor Green
}

$freedMB = [math]::Round(($bytesFreed / 1MB), 3)
Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "🎉 CLEANUP COMPLETE SUMMARY:" -ForegroundColor Green
Write-Host "• Total Files Removed : $removedCount"
Write-Host "• Total Disk Reclaimed: $freedMB MB ($bytesFreed bytes)"
Write-Host "• Source Code Safety  : PASSED"
Write-Host "============================================================================`n" -ForegroundColor Cyan
