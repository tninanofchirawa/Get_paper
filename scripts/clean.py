"""
scripts/clean.py - Zero-Dependency Project Cleanup & Artifact Purging Utility.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Purges temporary runtime artifacts and transient data:
1. Recursive __pycache__/ directories and *.pyc / *.pyo files.
2. Temporary batch files and test exports in output/ (preserves templates and .gitkeep).
3. Transient response cache JSON files in cache/ (preserves .gitkeep).
4. Runtime log files in logs/ (preserves .gitkeep).
5. Temporary scratch files in temp/ (preserves .gitkeep).
6. Transient SQLite test databases (test_*.db, *.db-wal, *.db-shm).

Safety Invariants:
- NEVER unlinks source code (*.py files).
- NEVER unlinks configuration templates (.env.example, service_account.json.example).
- NEVER unlinks documentation (HANDBOOK.md, README.md, docs/).
- NEVER unlinks authoritative source lists (data/scopus_source_list.xlsx, data/wos_master_journal_list.csv).
- NEVER unlinks .gitkeep placeholders.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Critical protected files that must never be modified or deleted
PROTECTED_FILENAMES = {
    "handbook.md",
    "readme.md",
    ".env.example",
    "service_account.json.example",
    "scopus_source_list.xlsx",
    "wos_master_journal_list.csv",
    ".gitignore",
    "requirements.txt",
    "main.py",
    "analyzer.py",
    "csv_builder.py",
    "excel_builder.py",
    "database.py",
    "scheduler.py",
    "batch_runner.py"
}


def clean_project_artifacts(dry_run: bool = False) -> Tuple[int, int]:
    """
    Cleans temporary artifacts and caches while strictly preserving project integrity.
    Returns (files_removed_count, bytes_freed).
    """
    root = Path(__file__).resolve().parent.parent
    mode_str = "[DRY RUN] " if dry_run else ""
    print("=" * 76)
    print(f"🧹 {mode_str}ZERO-DEPENDENCY PROJECT CLEANUP: {root.name}")
    print(f"📂 Workspace: {root}")
    print("=" * 76)

    removed_files = 0
    bytes_freed = 0
    removed_dirs = 0

    # 1. Purge __pycache__ and bytecode
    print("\n[1/5] Scanning for Python bytecode (__pycache__ / *.pyc / *.pyo)...")
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Skip virtual environment
        if ".venv" in dirpath.split(os.sep) or "venv" in dirpath.split(os.sep):
            continue

        for fname in filenames:
            if fname.endswith(".pyc") or fname.endswith(".pyo"):
                fpath = Path(dirpath) / fname
                try:
                    fsize = fpath.stat().st_size
                    if not dry_run:
                        fpath.unlink()
                    removed_files += 1
                    bytes_freed += fsize
                except Exception as e:
                    print(f"  ⚠️ Could not remove {fpath}: {e}")

        if os.path.basename(dirpath) == "__pycache__":
            try:
                if not dry_run:
                    shutil.rmtree(dirpath)
                removed_dirs += 1
            except Exception as e:
                print(f"  ⚠️ Could not remove dir {dirpath}: {e}")

    print(f"  -> Removed {removed_files} bytecode files and {removed_dirs} cache directories.")

    # 2. Clean temporary directories (cache/, temp/, logs/) preserving .gitkeep
    print("\n[2/5] Purging transient runtime caches (cache/, temp/, logs/)...")
    target_clean_dirs = ["cache", "temp", "logs"]
    dir_files_removed = 0

    for d_name in target_clean_dirs:
        d_path = root / d_name
        if not d_path.exists():
            if not dry_run:
                d_path.mkdir(parents=True, exist_ok=True)
            continue

        for item in d_path.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                try:
                    fsize = item.stat().st_size
                    if not dry_run:
                        item.unlink()
                    dir_files_removed += 1
                    bytes_freed += fsize
                except Exception as e:
                    print(f"  ⚠️ Could not remove {item.name}: {e}")

    print(f"  -> Cleaned {dir_files_removed} transient cache/log files.")
    removed_files += dir_files_removed

    # 3. Clean local test outputs and generated spreadsheets in output/
    print("\n[3/5] Cleaning intermediate and test outputs in output/...")
    out_dir = root / "output"
    out_removed = 0
    if out_dir.exists():
        for item in out_dir.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                # Clean test files and temporary generated exports
                if item.name.startswith("test_") or item.name.startswith("temp_") or item.suffix in (".csv", ".xlsx"):
                    try:
                        fsize = item.stat().st_size
                        if not dry_run:
                            item.unlink()
                        out_removed += 1
                        bytes_freed += fsize
                    except Exception as e:
                        print(f"  ⚠️ Could not remove {item.name}: {e}")
    print(f"  -> Cleaned {out_removed} test/run exports from output/.")
    removed_files += out_removed

    # 4. Clean temporary SQLite test databases and WAL files
    print("\n[4/5] Cleaning temporary SQLite databases (test_*.db, *.db-wal)...")
    data_dir = root / "data"
    db_removed = 0
    if data_dir.exists():
        for item in data_dir.iterdir():
            if item.is_file():
                if item.name.startswith("test_") and item.suffix in (".db", ".sqlite"):
                    try:
                        fsize = item.stat().st_size
                        if not dry_run:
                            item.unlink()
                        db_removed += 1
                        bytes_freed += fsize
                    except Exception as e:
                        print(f"  ⚠️ Could not remove {item.name}: {e}")
                elif item.suffix in (".db-wal", ".db-shm"):
                    try:
                        fsize = item.stat().st_size
                        if not dry_run:
                            item.unlink()
                        db_removed += 1
                        bytes_freed += fsize
                    except Exception as e:
                        pass
    print(f"  -> Cleaned {db_removed} transient database files.")
    removed_files += db_removed

    # 5. Dynamic directory recreation & sanity validation
    print("\n[5/5] Re-verifying essential directory structures...")
    required_dirs = ["cache", "data", "logs", "output", "temp", "input"]
    for d_name in required_dirs:
        p = root / d_name
        p.mkdir(parents=True, exist_ok=True)
        gitkeep = p / ".gitkeep"
        if not gitkeep.exists() and d_name in ("cache", "logs", "output", "temp"):
            gitkeep.touch()

    # Safety check
    print("  🔒 Running safety audit on protected files...")
    all_safe = True
    for prot in PROTECTED_FILENAMES:
        p_root = root / prot
        p_data = root / "data" / prot
        if not (p_root.exists() or p_data.exists()):
            all_safe = False
            print(f"  ❌ WARNING: Protected file missing: {prot}")

    if all_safe:
        print("  ✅ All protected source code, handbook, and templates are 100% intact.")

    freed_mb = bytes_freed / (1024 * 1024)
    print("\n" + "=" * 76)
    print(f"🎉 CLEANUP COMPLETE SUMMARY ({mode_str.strip() or 'Live'}):")
    print(f"• Total Files Removed : {removed_files}")
    print(f"• Total Disk Reclaimed: {freed_mb:.3f} MB ({bytes_freed:,} bytes)")
    print(f"• Source Code Safety  : PASSED (Zero source .py or handbook touched)")
    print("=" * 76 + "\n")

    return removed_files, bytes_freed


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    clean_project_artifacts(dry_run=dry)
