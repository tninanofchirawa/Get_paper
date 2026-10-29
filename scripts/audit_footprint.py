"""
scripts/audit_footprint.py - Backward compatibility wrapper delegating to scripts.audit.audit_footprint.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from scripts.audit.audit_footprint import audit_project_footprint

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    audit_project_footprint(target)
