"""
scripts/audit_footprint.py - Automated Project Footprint & Disk Usage Audit Utility.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Single-pass filesystem profiler:
1. Top 10 largest directories (MB).
2. Top 10 largest individual files (MB).
3. Inspection breakdown of common culprits (.venv, __pycache__, cache, db, output).
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def audit_project_footprint(root_dir: str = ".") -> Dict[str, Any]:
    root = Path(root_dir).resolve()
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

            if top_name != ".":
                top_dir_bytes[top_name] += size

            # Categorize culprits
            lower_rel = rel_file.lower().replace(os.sep, "/")
            if lower_rel.startswith(".venv/") or lower_rel.startswith("venv/"):
                culprit_bytes["Virtual Environment (.venv/ / venv/)"] += size
            elif "/__pycache__/" in lower_rel or lower_rel.endswith(".pyc") or lower_rel.endswith(".pyo"):
                culprit_bytes["Python Bytecode (__pycache__ / *.pyc)"] += size
            elif lower_rel.startswith(".git/"):
                culprit_bytes["Git Storage (.git/objects/)"] += size
            elif lower_rel.startswith("cache/") and lower_rel.endswith(".json"):
                culprit_bytes["Cache Directory (cache/*.json)"] += size
            elif lower_rel.endswith(".db") or lower_rel.endswith(".sqlite") or lower_rel.endswith(".sqlite3") or lower_rel.endswith(".db-wal"):
                culprit_bytes["SQLite Databases (*.db / *.sqlite)"] += size
            elif lower_rel.startswith("output/") and (lower_rel.endswith(".csv") or lower_rel.endswith(".xlsx")):
                culprit_bytes["Exported Spreadsheets (output/*.csv / *.xlsx)"] += size

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
        "Cache Directory (cache/*.json)",
        "SQLite Databases (*.db / *.sqlite)",
        "Exported Spreadsheets (output/*.csv / *.xlsx)"
    ]

    for cat in culprit_order:
        mb = culprit_bytes[cat] / (1024 * 1024)
        print(f"{cat:<48} {mb:>14.2f} MB")

    total_workspace_mb = sum(size for _, size in all_files) / (1024 * 1024)
    venv_mb = culprit_bytes["Virtual Environment (.venv/ / venv/)"] / (1024 * 1024)
    git_mb = culprit_bytes["Git Storage (.git/objects/)"] / (1024 * 1024)
    core_source_mb = total_workspace_mb - venv_mb - git_mb

    print("-" * 65)
    print(f"{'TOTAL ENTIRE WORKSPACE (including .venv)':<48} {total_workspace_mb:>14.2f} MB")
    print(f"{'VIRTUAL ENVIRONMENT (.venv)':<48} {venv_mb:>14.2f} MB")
    print(f"{'GIT VERSION CONTROL REPOSITORY (.git)':<48} {git_mb:>14.2f} MB")
    print(f"{'CORE PROJECT SOURCE CODE & ASSETS':<48} {core_source_mb:>14.2f} MB")
    print("=" * 80)

    if core_source_mb < 15.0:
        print(f"✅ [SUCCESS] Lean Footprint Goal Met: Core project is {core_source_mb:.2f} MB (< 15 MB threshold)!\n")
    else:
        print(f"⚠️ [NOTE] Core project source footprint is {core_source_mb:.2f} MB. Run clean.py or clean.ps1 to purge caches.\n")

    return {
        "total_mb": total_workspace_mb,
        "venv_mb": venv_mb,
        "git_mb": git_mb,
        "core_source_mb": core_source_mb,
        "directories": ranked_dirs[:10],
        "files": [(p, b / (1024*1024)) for p, b in all_files[:10]],
        "culprits": {k: b / (1024*1024) for k, b in culprit_bytes.items()}
    }


if __name__ == "__main__":
    audit_project_footprint()
