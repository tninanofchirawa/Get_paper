# scripts/maintenance/clean.ps1 - Zero-Dependency PowerShell Cleanup Utility for The_Paper_Getter
[CmdletBinding()]
param (
    [switch]$DryRun
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "🧹 $(if ($DryRun) { '[DRY RUN] ' })ZERO-DEPENDENCY PROJECT CLEANUP: The_Paper_Getter" -ForegroundColor Cyan
Write-Host "📂 Workspace: $root" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

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

# 2. Transient runtime caches (storage/cache/, storage/temp/, storage/logs/, cache/, temp/, logs/) preserving .gitkeep
Write-Host "`n[2/5] Purging transient caches (storage/cache/, storage/temp/, storage/logs/)..." -ForegroundColor Yellow
$targetDirs = @("storage\cache", "storage\temp", "storage\logs", "cache", "temp", "logs")
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
    }
}
Write-Host "  -> Cleaned $transientFiles transient files from cache/log directories."

# 3. Intermediate run outputs in storage/output/ & output/
Write-Host "`n[3/5] Cleaning test and intermediate exports in storage/output/..." -ForegroundColor Yellow
$outDirs = @("storage\output", "output")
$outRemoved = 0
foreach ($oName in $outDirs) {
    $outPath = Join-Path $root $oName
    if (Test-Path $outPath) {
        $outFiles = Get-ChildItem -Path $outPath -File -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -ne ".gitkeep" -and ($_.Name.StartsWith("test_") -or $_.Name.StartsWith("temp_") -or $_.Extension -match "\.(csv|xlsx)")
        }
        foreach ($f in $outFiles) {
            $bytesFreed += $f.Length
            $outRemoved++
            $removedCount++
            if (-not $DryRun) { Remove-Item -Force $f.FullName }
        }
    }
}
Write-Host "  -> Cleaned $outRemoved temporary export files."

# 4. SQLite test databases & WAL
Write-Host "`n[4/5] Cleaning temporary SQLite test databases and WAL files..." -ForegroundColor Yellow
$dataPath = Join-Path $root "data"
$dbRemoved = 0
if (Test-Path $dataPath) {
    $dbFiles = Get-ChildItem -Path $dataPath -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match "^test_.*\.db$" -or $_.Extension -match "\.(db-wal|db-shm)$"
    }
    foreach ($f in $dbFiles) {
        $bytesFreed += $f.Length
        $dbRemoved++
        $removedCount++
        if (-not $DryRun) { Remove-Item -Force $f.FullName }
    }
}
Write-Host "  -> Cleaned $dbRemoved temporary SQLite files."

# 5. Protected Assets Invariant Verification
Write-Host "`n[5/5] Verifying Protected Assets Invariant Integrity..." -ForegroundColor Yellow
$protectedAssets = @(
    @{ Name = "HANDBOOK.md"; Path = (Join-Path $root "HANDBOOK.md") },
    @{ Name = "README.md"; Path = (Join-Path $root "README.md") },
    @{ Name = "requirements.txt"; Path = (Join-Path $root "requirements.txt") },
    @{ Name = "Scopus Source List"; Path = (Join-Path $root "data\scopus_source_list.xlsx") },
    @{ Name = "WoS Master List"; Path = (Join-Path $root "data\wos_master_journal_list.csv") }
)

$allIntact = $true
foreach ($asset in $protectedAssets) {
    if (Test-Path $asset.Path) {
        Write-Host "  ✅ [INTACT] $($asset.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ [MISSING] $($asset.Name)" -ForegroundColor Red
        $allIntact = $false
    }
}

$freedMB = [Math]::Round($bytesFreed / 1MB, 2)
Write-Host "`n============================================================================" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "🔍 [DRY RUN COMPLETE] Would remove $removedCount files, freeing ~$freedMB MB." -ForegroundColor Cyan
} else {
    Write-Host "🎉 [CLEANUP COMPLETE] Removed $removedCount files, freed $freedMB MB." -ForegroundColor Green
}
Write-Host "============================================================================" -ForegroundColor Cyan
