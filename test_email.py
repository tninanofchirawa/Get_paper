"""
test_email.py - Backward compatibility shim delegating to scripts.audit.test_email.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.audit.test_email import (
    test_morning_intake,
    test_afternoon_reminder,
    test_night_reminder,
    test_correction_notice,
    test_run_success_summary,
    main,
)

if __name__ == "__main__":
    main()
