"""
scripts/clean.py - Backward compatibility wrapper delegating to scripts.maintenance.clean.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from scripts.maintenance.clean import clean_project_artifacts, PROTECTED_FILENAMES

if __name__ == "__main__":
    import sys
    is_dry = "--dry-run" in sys.argv or "-n" in sys.argv
    clean_project_artifacts(dry_run=is_dry)
