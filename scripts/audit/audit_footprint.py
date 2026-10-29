"""
scripts/audit/audit_footprint.py - Automated Project Footprint & Disk Usage Audit Utility.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Single-pass filesystem profiler:
1. Top 10 largest directories (MB).
2. Top 10 largest individual files (MB).
3. Inspection breakdown of common culprits (.venv, __pycache__, storage/cache, db, storage/output).
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def audit_project_footprint(root_dir: Optional[str] = None) -> Dict[str, Any]:
    root = Path(root_dir).resolve() if root_dir else PROJECT_ROOT
    print("=" * 80)
    print(f"📊 PROJECT FOOTPRINT & DISK AUDIT: {root.name}")
    print(f"📂 Root Path: {root}")
    print("=" * 80)

    # Accumulators
    top_dir_bytes: Dict[str, int] = defaultdict(int)
    all_files: List[Tuple[str, int]] = []
    culprit_bytes: Dict[str, int] = defaultdict(int)

    # Single-pass fast filesystem walk
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        top_name = rel_dir.split(os.sep)[0] if rel_dir != "." else "."

        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(full_path)
            except (PermissionError, FileNotFoundError):
                continue

            rel_file = os.path.relpath(full_path, root)
            all_files.append((rel_file, size))

            # Directory breakdown (top-level buckets)
            top_dir_bytes[top_name] += size

            # Culprit categorization
            norm_rel = rel_file.replace("\\", "/")
            if norm_rel.startswith(".venv/") or norm_rel.startswith("venv/"):
                culprit_bytes["Virtual Environment (.venv/ / venv/)"] += size
            elif "/__pycache__/" in norm_rel or norm_rel.endswith(".pyc"):
                culprit_bytes["Python Bytecode (__pycache__ / *.pyc)"] += size
            elif norm_rel.startswith(".git/"):
                culprit_bytes["Git Storage (.git/objects/)"] += size
            elif norm_rel.startswith("storage/cache/") or norm_rel.startswith("cache/"):
                culprit_bytes["Cache Directory (storage/cache/*.json)"] += size
            elif norm_rel.endswith(".db") or norm_rel.endswith(".sqlite") or ".db-" in norm_rel:
                culprit_bytes["SQLite Databases (*.db / *.sqlite)"] += size
            elif norm_rel.startswith("storage/output/") or norm_rel.startswith("output/") or norm_rel.endswith(".csv") or norm_rel.endswith(".xlsx"):
                if "scopus_source_list" not in norm_rel and "wos_master_journal" not in norm_rel:
                    culprit_bytes["Exported Spreadsheets (storage/output/*.csv / *.xlsx)"] += size

    total_bytes = sum(s for _, s in all_files)
    total_mb = total_bytes / (1024 * 1024)

    # 1. Directory Profiling
    ranked_dirs = sorted(
        [(name, size / (1024 * 1024)) for name, size in top_dir_bytes.items()],
        key=lambda x: x[1],
        reverse=True
    )

    print("\n📁 TOP 10 LARGEST DIRECTORIES (Ranked by MB):")
    print("-" * 55)
    print(f"{'Rank':<6} {'Directory Name':<32} {'Size (MB)':>12}")
    print("-" * 55)
    for idx, (d_name, d_size) in enumerate(ranked_dirs[:10], 1):
        print(f"{idx:<6} {d_name:<32} {d_size:>12.2f} MB")
    print("-" * 55)

    # 2. File Profiling
    all_files.sort(key=lambda x: x[1], reverse=True)

    print("\n📄 TOP 10 LARGEST INDIVIDUAL FILES (Ranked by MB):")
    print("-" * 80)
    print(f"{'Rank':<6} {'Relative Path':<56} {'Size (MB)':>14}")
    print("-" * 80)
    for idx, (f_path, f_size_bytes) in enumerate(all_files[:10], 1):
        f_size_mb = f_size_bytes / (1024 * 1024)
        display_path = f_path if len(f_path) <= 55 else "..." + f_path[-52:]
        print(f"{idx:<6} {display_path:<56} {f_size_mb:>14.3f} MB")
    print("-" * 80)

    # 3. Culprit Breakdown
    print("\n🔍 COMMON DISK SPACE CULPRITS BREAKDOWN:")
    print("-" * 65)
    print(f"{'Culprit Category':<48} {'Size (MB)':>14}")
    print("-" * 65)

    culprit_order = [
        "Virtual Environment (.venv/ / venv/)",
        "Python Bytecode (__pycache__ / *.pyc)",
        "Git Storage (.git/objects/)",
        "Cache Directory (storage/cache/*.json)",
        "SQLite Databases (*.db / *.sqlite)",
        "Exported Spreadsheets (storage/output/*.csv / *.xlsx)"
    ]

    for category in culprit_order:
        c_bytes = culprit_bytes.get(category, 0)
        c_mb = c_bytes / (1024 * 1024)
        print(f"{category:<48} {c_mb:>14.2f} MB")
    print("-" * 65)

    print(f"\n📦 TOTAL PROJECT DISK USAGE: {total_mb:.2f} MB ({len(all_files)} total files)")
    print("=" * 80 + "\n")

    return {
        "total_bytes": total_bytes,
        "total_files": len(all_files),
        "top_dirs": ranked_dirs,
        "top_files": all_files[:10],
        "culprits": dict(culprit_bytes)
    }


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    audit_project_footprint(target)
