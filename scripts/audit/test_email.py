"""
test_email.py - Visual verification test script for rich HTML email templates.
Dispatches all upgraded email templates to RECIPIENT_EMAIL for visual confirmation.
"""

import os
import sys
import argparse
import datetime
from pathlib import Path

# Dynamic project root path resolution
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import cfg
from email_service import email_dispatcher, get_ist_now
from harvester.models import Paper
from analyzer import PaperAnalyzer
from excel_builder import StandardizedExcelBuilder
from csv_builder import StandardizedCsvBuilder


def test_morning_intake(recipient: str, date_str: str):
    print(f"\n1️⃣ [Dispatching] 🌅 Morning Intake Questionnaire to {recipient}...")
    success = email_dispatcher.send_morning_intake_questionnaire(date_str=date_str, recipient=recipient)
    status = "✅ SENT" if success else "❌ FAILED"
    print(f"   Result: {status}")


def test_afternoon_reminder(recipient: str, date_str: str):
    print(f"\n2️⃣ [Dispatching] ☀️ Afternoon Catch-Up Notice to {recipient}...")
    success = email_dispatcher.send_afternoon_reminder(date_str=date_str, recipient=recipient)
    status = "✅ SENT" if success else "❌ FAILED"
    print(f"   Result: {status}")


def test_night_reminder(recipient: str, date_str: str):
    print(f"\n3️⃣ [Dispatching] 🌙 Night Check-In Notice to {recipient}...")
    success = email_dispatcher.send_night_reminder(date_str=date_str, recipient=recipient)
    status = "✅ SENT" if success else "❌ FAILED"
    print(f"   Result: {status}")


def test_correction_notice(recipient: str, date_str: str):
    print(f"\n4️⃣ [Dispatching] ⚠️ Parameter Adjustment Needed Notice to {recipient}...")
    sample_errors = [
        "❌ [PAPERS_PER_TOPIC]: You requested 700 papers. (The hard ceiling is 500 papers per topic to prevent API blocks).",
        "❌ [T1_SUBTOPICS]: You provided 7 subtopics. (Maximum allowed is 5)."
    ]
    sample_body = "[PAPERS_PER_TOPIC]: 700\n[T1_SUBTOPICS]: S1, S2, S3, S4, S5, S6, S7"
    success = email_dispatcher.send_corrective_email(
        recipient=recipient,
        errors=sample_errors,
        raw_body=sample_body,
        date_str=date_str
    )
    status = "✅ SENT" if success else "❌ FAILED"
    print(f"   Result: {status}")


def test_completion_report(recipient: str, date_str: str):
    print(f"\n5️⃣ [Dispatching] ✅ Run Completion & Dispatch Report to {recipient}...")

    # Generate sample standardized CSV file for attachment
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    sample_csv = os.path.join(cfg.OUTPUT_DIR, f"Test_Run_{date_str}_verified.csv")

    sample_papers = [
        Paper(
            title="Type-2 Fuzzy Logic Systems for Dynamic Control",
            authors="Jerry M. Mendel; Nilesh N. Karnik",
            year="2022",
            venue="IEEE Transactions on Fuzzy Systems",
            doi="10.1109/TFUZZ.2022.1001",
            url="https://doi.org/10.1109/TFUZZ.2022.1001",
            scopus_indexed=True,
            wos_indexed=True,
            ieee_indexed=True,
            open_access=False,
            verified_sources=["Scopus", "Web of Science", "IEEE Xplore"],
            verification_source="Elsevier Scopus, WoS Expanded, IEEE Xplore"
        ),
        Paper(
            title="Deep Learning with Fuzzy Granular Information",
            authors="Witold Pedrycz; Kaoru Hirota",
            year="2024",
            venue="Information Sciences",
            doi="10.1016/j.ins.2024.1002",
            url="https://doi.org/10.1016/j.ins.2024.1002",
            scopus_indexed=True,
            wos_indexed=True,
            ieee_indexed=False,
            open_access=True,
            verified_sources=["Scopus", "OpenAlex", "Crossref"],
            verification_source="Local Scopus DB, OpenAlex Registry, Crossref"
        )
    ]

    analyzed = [
        PaperAnalyzer.analyze_paper(sample_papers[0], query="Fuzzy Logic", material_idx=1),
        PaperAnalyzer.analyze_paper(sample_papers[1], query="Granular Computing", material_idx=2)
    ]

    run_config = {
        "run_name": f"Visual_Test_Run_{date_str}",
        "run_type": "Automated Scheduled",
        "location": "HITS Campus",
        "main_topics": ["Fuzzy Machine Learning", "Graph Neural Networks"],
        "topics": ["Fuzzy Machine Learning", "Graph Neural Networks"],
        "subtopics": ["T-Norms", "Type-2 Fuzzy Logic"],
        "harvest_quota": 250,
        "inst_token_flag": True
    }

    metrics = {
        "raw_scraped": 284,
        "duplicates_removed": 34,
        "verified_retained": 250,
        "excluded_non_indexed": 12,
        "duration_seconds": 84,
        "scopus_hits": 218,
        "wos_hits": 194,
        "ieee_hits": 142,
        "crossref_hits": 180,
        "open_access_hits": 96,
        "arxiv_hits": 24,
        "semantic_scholar_hits": 110,
        "drive_link": "https://drive.google.com/file/d/sample_test_drive_id/view"
    }

    StandardizedCsvBuilder.generate_csv(
        papers=analyzed,
        run_config=run_config,
        metrics=metrics,
        output_filepath=sample_csv
    )

    success = email_dispatcher.send_run_completion_report(
        run_config=run_config,
        metrics=metrics,
        csv_path=sample_csv,
        papers=analyzed,
        drive_link=metrics["drive_link"],
        recipient=recipient
    )
    status = "✅ SENT" if success else "❌ FAILED"
    print(f"   Result: {status}")


def main():
    parser = argparse.ArgumentParser(description="Test and visually verify redesigned rich email templates")
    parser.add_argument("--to", type=str, default=cfg.RECIPIENT_EMAIL, help="Recipient email address")
    parser.add_argument("--type", type=str, choices=["all", "morning", "afternoon", "night", "correction", "report"], default="all", help="Template to test")
    args = parser.parse_args()

    recipient = args.to or "researcher@university.edu"
    date_str = get_ist_now().strftime("%Y-%m-%d")

    print("\n" + "=" * 76)
    print("✨ RICH EMAIL TEMPLATE VISUAL VERIFICATION SUITE")
    print("=" * 76)
    print(f"📧 Destination : {recipient}")
    print(f"⚙️ Provider    : {cfg.EMAIL_PROVIDER.upper()} (SMTP Host: {cfg.SMTP_HOST})")
    print(f"🗓️ Date Stamp  : {date_str}")
    print("=" * 76)

    if args.type in ("all", "morning"):
        test_morning_intake(recipient, date_str)
    if args.type in ("all", "afternoon"):
        test_afternoon_reminder(recipient, date_str)
    if args.type in ("all", "night"):
        test_night_reminder(recipient, date_str)
    if args.type in ("all", "correction"):
        test_correction_notice(recipient, date_str)
    if args.type in ("all", "report"):
        test_completion_report(recipient, date_str)

    print("\n" + "=" * 76)
    print("🎉 Visual verification dispatch completed!")
    print("Check your email inbox or console output above to confirm rendering.")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
