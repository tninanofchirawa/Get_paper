"""
main.py - Central CLI and Runtime Engine for Unified Academic Paper Harvester & Verifier.
Unified Academic Paper Harvester, Verifier & 100% Gmail-Driven Notification Pipeline.
"""

import os
import sys
import argparse
import asyncio
import datetime
from pathlib import Path

# Ensure UTF-8 console encoding on Windows
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
from core.database import db
from services.cache.cleaner import purge_stale_cache, purge_nightly_cache
from harvester.pipeline import AsyncHarvestingPipeline
from verifier.dual_branch import DualBranchVerifier
from core.analyzer import PaperAnalyzer
from utils.excel_builder import StandardizedExcelBuilder
from utils.csv_builder import StandardizedCsvBuilder
from core.batch_runner import ResilientBatchRunner
from services.drive import drive_client
from services.notifications import email_dispatcher


async def run_spontaneous(
    query: str,
    target_quota: int = 250,
    inst_token: bool = False,
    year_range: str = "All Years",
    doc_filter: str = "All",
    quota_strictness: str = "Strict",
    only_indexed: bool = False,
    run_name_override: str = None,
    output_path: str = None
) -> str:
    """Executes single query literature harvesting, multi-source academic verification, and CSV generation."""
    run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_name = run_name_override or f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    run_config = {
        "run_name": run_name,
        "run_type": "Spontaneous Manual",
        "location": "Home",
        "topics": [query],
        "harvest_quota": target_quota,
        "year_range": year_range,
        "doc_filter": doc_filter,
        "inst_token_flag": inst_token,
        "quota_strictness": quota_strictness,
        "only_indexed": only_indexed,
        "target_repos": ["Scopus", "Web of Science", "IEEE Xplore", "OpenAlex", "Crossref", "arXiv"] if inst_token else ["OpenAlex", "Crossref", "arXiv"]
    }

    db.log_run_start(run_id, run_name, run_config)
    print("\n" + "=" * 76)
    print(f"🎓 UNIFIED ACADEMIC PAPER HARVESTER & VERIFIER PIPELINE v{cfg.APP_VERSION}")
    print("=" * 76)
    print(f"🔍 Query           : {query}")
    print(f"🎯 Target Quota    : {target_quota} papers")
    print(f"🏛️ Institutional   : {'Enabled (Scopus/WoS/IEEE)' if inst_token else 'Open Access Fallback (OpenAlex/Crossref/arXiv/Local DB)'}")
    print(f"🎯 Strict Filtering: {'Enabled (Scopus/WoS Only)' if only_indexed else 'Disabled (Broad Open Access Fallbacks)'}")
    print(f"⚡ Mode             : {quota_strictness}")
    print("=" * 76 + "\n")

    pipeline = AsyncHarvestingPipeline()
    verifier = DualBranchVerifier(inst_token_flag=inst_token)

    papers, metrics = await pipeline.harvest(
        query=query,
        target_quota=target_quota,
        year_range=year_range,
        doc_filter=doc_filter,
        quota_strictness=quota_strictness
    )

    print(f"\n🔍 [Verification] Concurrently verifying {len(papers)} candidate papers across academic aggregators...")
    verified_papers = verifier.verify_batch(papers, only_indexed=only_indexed)
    excluded_count = verifier.last_excluded_count

    print(f"📊 [Analysis] Enriching records with taxonomy classifications and analytical metadata...")
    analyzed_papers = []
    for idx, p in enumerate(verified_papers, 1):
        ap = PaperAnalyzer.analyze_paper(p, query=query, material_idx=idx)
        analyzed_papers.append(ap)

    out_file = output_path or os.path.join(cfg.OUTPUT_DIR, f"{run_name}.csv")
    if out_file.lower().endswith(".xlsx"):
        out_file = out_file[:-5] + ".csv"

    final_metrics = {
        "raw_scraped": metrics["raw_scraped"],
        "duplicates_removed": metrics["duplicates_removed"],
        "verified_retained": len(analyzed_papers),
        "excluded_non_indexed": excluded_count
    }

    # Primary export: Standardized UTF-8 CSV
    csv_path = StandardizedCsvBuilder.generate_csv(
        papers=analyzed_papers,
        run_config=run_config,
        metrics=final_metrics,
        output_filepath=out_file
    )

    # Google Drive v3 upload if configured (with supportsAllDrives=True and payload size validation)
    drive_id = drive_client.upload_file(csv_path, custom_filename=f"{run_name}.csv")
    drive_link = drive_client.get_last_link()
    final_metrics["drive_link"] = drive_link

    # Log completion in SQLite
    db.log_run_completion(
        run_id=run_id,
        raw_scraped=final_metrics["raw_scraped"],
        duplicates_removed=final_metrics["duplicates_removed"],
        verified_retained=final_metrics["verified_retained"],
        failed_calls=0,
        excel_path=csv_path,
        drive_file_id=drive_id,
        status="COMPLETED"
    )
    db.mark_daily_run_completed()

    # Dispatch completion email with robust exception handling
    try:
        email_dispatcher.send_run_completion_report(
            run_config=run_config,
            metrics=final_metrics,
            csv_path=csv_path,
            papers=analyzed_papers,
            drive_link=drive_link,
            drive_file_id=drive_id
        )
    except Exception as e:
        print(f"⚠️ [Email Dispatch Warning] Could not deliver email report: {e} (Drive sync & logs preserved).")

    # Clean cache immediately following completed run
    purge_stale_cache()

    print("\n" + "=" * 76)
    print("🎉 EXECUTION COMPLETE SUMMARY:")
    print(f"• Run Name                 : {run_name}")
    print(f"• Total Raw Scraped        : {final_metrics['raw_scraped']}")
    print(f"• Total Duplicates Removed : {final_metrics['duplicates_removed']}")
    print(f"• Verified Papers Retained : {final_metrics['verified_retained']}")
    print(f"• Excluded Non-Indexed     : {excluded_count}")
    print(f"• Standard CSV Generated   : {csv_path}")
    if drive_id:
        print(f"• Google Drive File ID     : {drive_id}")
        if drive_link:
            print(f"• Google Drive Link        : {drive_link}")
    print("=" * 76 + "\n")
    return csv_path


def interactive_terminal_intake():
    """Provides interactive 15-point intake directly in the console."""
    print("\n" + "=" * 76)
    print("   UNIFIED ACADEMIC PAPER HARVESTER - 15-POINT TERMINAL INTAKE")
    print("=" * 76)

    try:
        r_name = input("\n[1/15] Run Name (Press Enter for auto timestamp): ").strip()
        run_name = r_name if r_name else f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print("[2/15] Type of Run: [1] Automated Scheduled  [2] Spontaneous Manual  [3] Batch File Run")
        t_sel = input("Choice (default: 2): ").strip()
        run_type = {"1": "Automated Scheduled", "2": "Spontaneous Manual", "3": "Batch File Run"}.get(t_sel, "Spontaneous Manual")

        print("[3/15] Execution Location: [1] HITS Campus  [2] Home  [3] Online Remote VPS")
        l_sel = input("Choice (default: 2): ").strip()
        location = {"1": "HITS Campus", "2": "Home", "3": "Online Remote VPS"}.get(l_sel, "Home")

        b_sel = input("[4/15] Batch Execution across all input files? (y/N): ").strip().lower()
        is_batch = b_sel in ("y", "yes", "1")

        if is_batch:
            runner = ResilientBatchRunner()
            run_config = {
                "run_name": run_name,
                "run_type": run_type,
                "location": location,
                "is_batch": True,
                "inst_token_flag": cfg.has_institutional_credentials
            }
            runner.run_all(f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}", run_config)
            return

        m_topic = input("\n[8 & 9/15] Enter Main Topic (e.g. Fuzzy Logic & Neural Networks): ").strip()
        if not m_topic:
            m_topic = "fuzzy logic"
        s_topics = input("Enter up to 5 subtopics (comma separated, or press Enter): ").strip()
        subtopic_list = [s.strip() for s in s_topics.split(",") if s.strip()][:5]
        full_query = f"{m_topic} {' '.join(subtopic_list)}".strip()

        q_in = input("\n[10/15] Target Quota per topic [100, 250, 500] (default: 250): ").strip()
        quota = int(q_in) if q_in.isdigit() else 250
        quota = min(quota, cfg.HARD_CAP_QUOTA_PER_TOPIC)

        y_in = input("[11/15] Year Range (e.g. 2021-2026 or Enter for All Years): ").strip()
        year_range = y_in if y_in else "All Years"

        print("[12/15] Document Filter: [1] All  [2] Journal Articles  [3] Conferences  [4] Preprints")
        d_sel = input("Choice (default: 1): ").strip()
        doc_filter = {"1": "All", "2": "Journal Articles Only", "3": "Conference Proceedings", "4": "Preprints"}.get(d_sel, "All")

        has_inst = cfg.has_institutional_credentials
        inst_in = input(f"[13/15] Enable Institutional Token (Scopus/WoS/IEEE)? (y/N, default: {'Y' if has_inst else 'N'}): ").strip().lower()
        inst_token = inst_in in ("y", "yes") if inst_in else has_inst

        oi_in = input("[14/15] Filter for indexed-only papers (Scopus / Web of Science)? [y/N]: ").strip().lower()
        only_indexed = oi_in in ("y", "yes", "1")

        print("[15/15] Quota Strictness: [1] Strict (Paginate until quota met)  [2] Fast/Capped")
        st_sel = input("Choice (default: 1): ").strip()
        quota_strictness = "Strict" if st_sel != "2" else "Fast/Capped"

        asyncio.run(run_spontaneous(
            query=full_query,
            target_quota=quota,
            inst_token=inst_token,
            year_range=year_range,
            doc_filter=doc_filter,
            quota_strictness=quota_strictness,
            only_indexed=only_indexed,
            run_name_override=run_name
        ))

    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")


def interactive_menu():
    """Main terminal menu."""
    print("\n" + "=" * 76)
    print(f"🎓 UNIFIED ACADEMIC PAPER HARVESTER, VERIFIER & NOTIFICATION ENGINE")
    print("=" * 76)
    print(f"📧 Gmail / Polite Pool : {cfg.POLITE_EMAIL}")
    print(f"🏛️ Scopus Credentials  : {'API Key + Token PRESENT' if cfg.has_scopus_credentials else 'MISSING (Fallback Active)'}")
    print(f"🗄️ Database Path       : {cfg.DATABASE_PATH}")
    print(f"📂 Input Directory     : {cfg.INPUT_DIR}")
    print(f"📁 Output Directory    : {cfg.OUTPUT_DIR}")
    print("-" * 76)
    print("Select Execution Mode:")
    print("  [1] Interactive 15-Point Questionnaire Intake (Terminal)")
    print("  [2] Fast Spontaneous Harvest (Default query: 'fuzzy neural networks')")
    print("  [3] Process ALL CSV Files in 'input/' (Deterministic Batch Runner)")
    print("  [4] Start Three-Tier Reminder Scheduler & IMAP Listener Daemon (07:30 AM / 02:00 PM / 09:00 PM IST)")
    print("  [5] Test Reminder Dispatch Immediately (Morning / Afternoon / Night via SMTP)")
    print("  [6] Purge Stale Cache (Automated 48-Hour TTL Cleaner)")
    print("  [7] Run Package Test Suite")
    print("  [0] Exit")
    print("=" * 76)

    try:
        choice = input("Enter selection [1-7, 0 to exit]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return 0

    if choice == "1":
        interactive_terminal_intake()
    elif choice == "2":
        q = input("Enter research query [default: 'fuzzy neural networks']: ").strip() or "fuzzy neural networks"
        quota_in = input("Enter target quota [default: 250]: ").strip()
        quota = int(quota_in) if quota_in.isdigit() else 250
        oi_in = input("Filter for indexed-only papers (Scopus/WoS)? [y/N]: ").strip().lower()
        only_idx = oi_in in ("y", "yes", "1")
        asyncio.run(run_spontaneous(query=q, target_quota=quota, only_indexed=only_idx))
    elif choice == "3":
        runner = ResilientBatchRunner()
        oi_in = input("Filter for indexed-only papers in batch (Scopus/WoS)? [y/N]: ").strip().lower()
        only_idx = oi_in in ("y", "yes", "1")
        run_config = {
            "run_name": f"Batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "run_type": "Batch File Run",
            "location": "Home",
            "is_batch": True,
            "only_indexed": only_idx,
            "inst_token_flag": cfg.has_institutional_credentials
        }
        runner.run_all(f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}", run_config)
    elif choice == "4":
        from scheduler import scheduler
        asyncio.run(scheduler.run_daemon())
    elif choice == "5":
        from scheduler import scheduler
        print("\nSelect tier: [1] Morning (07:30 AM)  [2] Afternoon (02:00 PM)  [3] Night (09:00 PM)")
        t_sel = input("Choice: ").strip()
        tier_name = {"1": "morning", "2": "afternoon", "3": "night"}.get(t_sel, "morning")
        scheduler.check_and_dispatch(force_tier=tier_name)
        print("Reminder dispatched successfully.")
    elif choice == "6":
        purge_stale_cache()
    elif choice == "7":
        import unittest
        suite = unittest.defaultTestLoader.discover("tests")
        unittest.TextTestRunner(verbosity=2).run(suite)
    elif choice == "0":
        print("Exiting.")
        return 0
    return 0


def main():
    # Purge stale cache on bootup as required by Section 2
    purge_stale_cache()

    parser = argparse.ArgumentParser(description="Unified Academic Paper Harvester, Verifier & 100% Gmail-Driven Pipeline")
    parser.add_argument("--query", type=str, help="Search query for literature harvesting")
    parser.add_argument("--quota", type=int, default=250, help="Target paper quota")
    parser.add_argument("--run-name", type=str, help="Dynamic run name / query identifier across CSV, Drive, and Email")
    parser.add_argument("--only-indexed", action="store_true", help="Filter for indexed-only papers (Scopus or Web of Science)")
    parser.add_argument("--all", "--batch", action="store_true", help="Process all datasets in input/ directory")
    parser.add_argument("--scheduler", action="store_true", help="Launch 3-tier IST reminder scheduler and IMAP listener daemon")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    parser.add_argument("--clear-cache", "--clean-cache", action="store_true", help="Flush cache directory and transient artifacts on demand")
    parser.add_argument("--check-reminders", action="store_true", help="Check and dispatch pending reminders")
    parser.add_argument("--tier", type=str, help="Force reminder tier (morning, afternoon, night)")

    args = parser.parse_args()

    if args.clear_cache:
        purge_nightly_cache(force_all=True)
    elif args.scheduler:
        from scheduler import scheduler
        asyncio.run(scheduler.run_daemon())
    elif args.check_reminders:
        from scheduler import scheduler
        scheduler.check_and_dispatch(force_tier=args.tier)
    elif args.test:
        import unittest
        suite = unittest.defaultTestLoader.discover("tests")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    elif args.all:
        runner = ResilientBatchRunner()
        run_config = {
            "run_name": args.run_name or f"Batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "run_type": "Batch File Run",
            "is_batch": True,
            "only_indexed": args.only_indexed,
            "inst_token_flag": cfg.has_institutional_credentials
        }
        runner.run_all(f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}", run_config)
    elif args.query:
        asyncio.run(run_spontaneous(
            query=args.query,
            target_quota=args.quota,
            only_indexed=args.only_indexed,
            run_name_override=args.run_name
        ))
    else:
        sys.exit(interactive_menu())


if __name__ == "__main__":
    main()
