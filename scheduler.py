"""
scheduler.py - Three-tier scheduled reminders daemon (07:30 AM, 02:00 PM, 09:00 PM IST) & IMAP listener.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import sys
import time
import asyncio
import datetime
from datetime import timezone, timedelta
import logging
from typing import Dict, Any, Optional

from config import cfg
from core.database import db
from services.notifications import email_dispatcher, imap_reader, parse_run_config_tags
from services.cache.cleaner import purge_stale_cache, purge_nightly_cache
from harvester.pipeline import AsyncHarvestingPipeline
from verifier.dual_branch import DualBranchVerifier
from core.analyzer import PaperAnalyzer
from utils.excel_builder import StandardizedExcelBuilder
from utils.csv_builder import StandardizedCsvBuilder
from services.drive import drive_client
from core.batch_runner import ResilientBatchRunner

logger = logging.getLogger("SchedulerDaemon")


def get_ist_now() -> datetime.datetime:
    """Returns the current datetime in Indian Standard Time (IST, UTC+5:30)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_tz)


async def execute_email_triggered_pipeline(run_config: Dict[str, Any], sender_email: str):
    """
    Asynchronously executes the paper harvesting, dual-branch verification,
    Excel generation, Drive sync, and completion email delivery triggered by an inbound email.
    """
    start_time = time.time()
    run_name = run_config.get("run_name", f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    run_id = f"run_email_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n🚀 [Pipeline Triggered] Inbound email run '{run_name}' started for {sender_email}...")
    db.log_run_start(run_id, run_name, run_config)

    try:
        # Check if Batch Run requested
        if run_config.get("is_batch"):
            runner = ResilientBatchRunner()
            summary = runner.run_all(run_id, run_config)
            out_file = os.path.join(cfg.OUTPUT_DIR, f"{run_name}_batch_summary.xlsx")
            final_metrics = {
                "raw_scraped": summary["total_files"],
                "duplicates_removed": 0,
                "verified_retained": summary["completed"],
                "duration_seconds": int(time.time() - start_time)
            }
            # Upload & Dispatch email
            drive_id = drive_client.upload_file(out_file) if os.path.exists(out_file) else None
            db.log_run_completion(
                run_id=run_id,
                raw_scraped=final_metrics["raw_scraped"],
                duplicates_removed=0,
                verified_retained=final_metrics["verified_retained"],
                failed_calls=summary["failed"],
                excel_path=out_file if os.path.exists(out_file) else "",
                drive_file_id=drive_id,
                status="COMPLETED"
            )
            db.mark_daily_run_completed()
            purge_stale_cache()
            return

        # Spontaneous / Configured Topic Harvest
        topics = run_config.get("topics", [run_config.get("main_topic", "fuzzy logic")])
        quota_per_topic = run_config.get("harvest_quota", cfg.DEFAULT_QUOTA)
        subtopics_map = run_config.get("subtopics_map", {})

        pipeline = AsyncHarvestingPipeline()
        verifier = DualBranchVerifier(inst_token_flag=run_config.get("inst_token_flag", False))

        all_harvested_papers = []
        total_raw = 0
        total_dups = 0

        for topic in topics:
            subs = subtopics_map.get(topic, [])
            sub_str = " ".join(subs[:3]) if subs else ""
            query_str = f"{topic} {sub_str}".strip()

            papers, metrics = await pipeline.harvest(
                query=query_str,
                target_quota=quota_per_topic,
                year_range=run_config.get("year_range", "All Years"),
                doc_filter=run_config.get("doc_filter", "All"),
                quota_strictness=run_config.get("quota_strictness", "Strict")
            )
            all_harvested_papers.extend(papers)
            total_raw += metrics.get("raw_scraped", 0)
            total_dups += metrics.get("duplicates_removed", 0)

        # Multi-source academic verification
        print(f"🔍 [Verification] Verifying {len(all_harvested_papers)} candidate papers...")
        only_indexed = run_config.get("only_indexed", False)
        verified_papers = verifier.verify_batch(all_harvested_papers, only_indexed=only_indexed)
        excluded_count = getattr(verifier, "last_excluded_count", 0)

        # Taxonomy enrichment
        analyzed_papers = []
        for idx, p in enumerate(verified_papers, 1):
            ap = PaperAnalyzer.analyze_paper(p, query=run_config.get("main_topic", topics[0]), material_idx=idx)
            analyzed_papers.append(ap)

        # Standardized UTF-8 CSV build
        out_file = os.path.join(cfg.OUTPUT_DIR, f"{run_name}.csv")
        final_metrics = {
            "raw_scraped": total_raw,
            "duplicates_removed": total_dups,
            "verified_retained": len(analyzed_papers),
            "excluded_non_indexed": excluded_count,
            "duration_seconds": int(time.time() - start_time)
        }

        StandardizedCsvBuilder.generate_csv(
            papers=analyzed_papers,
            run_config=run_config,
            metrics=final_metrics,
            output_filepath=out_file
        )

        # Google Drive v3 sync
        drive_id = drive_client.upload_file(out_file, custom_filename=f"{run_name}.csv")
        drive_link = drive_client.get_last_link()
        final_metrics["drive_link"] = drive_link

        # Log completion
        db.log_run_completion(
            run_id=run_id,
            raw_scraped=total_raw,
            duplicates_removed=total_dups,
            verified_retained=len(analyzed_papers),
            failed_calls=0,
            excel_path=out_file,
            drive_file_id=drive_id,
            status="COMPLETED"
        )

        # Mark daily run as completed
        db.mark_daily_run_completed()

        # Send completion email to sender with robust exception handling
        try:
            email_dispatcher.send_run_completion_report(
                run_config=run_config,
                metrics=final_metrics,
                csv_path=out_file,
                papers=analyzed_papers,
                drive_link=drive_link,
                drive_file_id=drive_id,
                recipient=sender_email
            )
        except Exception as e:
            print(f"⚠️ [Email Dispatch Warning] Could not deliver email report: {e}")

        # Self-cleaning cache purge immediately following completed run
        purge_stale_cache()

        print(f"✅ [Pipeline Finished] Successfully completed email run '{run_name}'. Daily run flag set to True.\n")

    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[Email Trigger Pipeline ERROR] {err_msg}")
        print(f"❌ [Email Trigger Pipeline ERROR] {err_msg}")
        db.log_run_completion(
            run_id=run_id,
            raw_scraped=0,
            duplicates_removed=0,
            verified_retained=0,
            failed_calls=1,
            excel_path="",
            status="FAILED",
            error_message=err_msg
        )


class ThreeTierScheduler:
    """
    Maintains persistent daily state in SQLite and dispatches:
    1. 07:30 AM IST - Morning Intake Questionnaire via Gmail SMTP
    2. 02:00 PM IST - Afternoon Catch-Up Reminder via Gmail SMTP
    3. 09:00 PM IST - Final Night Reminder via Gmail SMTP
    Suppresses remaining reminders once daily_run_completed is True.
    Resets daily_run_completed = False at midnight (00:00 IST).
    Polls inbound IMAP inbox every 2 minutes for '[Harvester Run Config]'.
    """

    def __init__(self):
        self.running = False
        self.last_checked_date: Optional[str] = None

    def check_and_dispatch(self, force_tier: Optional[str] = None):
        """Evaluates daily state and dispatches scheduled reminders if applicable."""
        now_ist = get_ist_now()
        date_str = now_ist.strftime("%Y-%m-%d")
        current_hour = now_ist.hour
        current_minute = now_ist.minute
        time_decimal = current_hour + (current_minute / 60.0)

        # Midnight Reset Check (00:00 IST)
        if self.last_checked_date and self.last_checked_date != date_str:
            print(f"🌙 [Scheduler] Midnight rollover: New IST date {date_str}. Resetting daily_run_completed = False.")
            logger.info(f"[Scheduler] Midnight rollover: Resetting daily_run_completed = False for {date_str}.")
            db.reset_daily_state_for_midnight(date_str)
            purge_nightly_cache()

        self.last_checked_date = date_str

        state = db.get_or_create_daily_state(date_str)
        is_completed = bool(state.get("daily_run_completed", 0))

        if is_completed and not force_tier:
            logger.debug(f"[Scheduler] Daily run for {date_str} already completed. Reminders suppressed.")
            return

        # Tier 1: Morning Intake Questionnaire (07:30 AM IST = 7.50)
        if force_tier == "morning" or (time_decimal >= 7.5 and not state.get("morning_sent", 0)):
            # Self-cleaning purge before scheduled intake fires
            purge_stale_cache()
            print(f"\n🌅 [Scheduler] Dispatching Tier 1 Morning Intake Questionnaire ({now_ist.strftime('%I:%M %p IST')})...")
            email_dispatcher.send_questionnaire_email("morning", date_str)
            db.mark_reminder_sent("morning", date_str)

        # Tier 2: Afternoon Catch-Up Reminder (02:00 PM IST = 14.00)
        elif force_tier == "afternoon" or (time_decimal >= 14.0 and not state.get("afternoon_sent", 0)):
            purge_stale_cache()
            print(f"\n☀️ [Scheduler] Dispatching Tier 2 Afternoon Reminder ({now_ist.strftime('%I:%M %p IST')})...")
            email_dispatcher.send_questionnaire_email("afternoon", date_str)
            db.mark_reminder_sent("afternoon", date_str)

        # Tier 3: Final Night Reminder (09:00 PM IST = 21.00)
        elif force_tier == "night" or (time_decimal >= 21.0 and not state.get("night_sent", 0)):
            purge_stale_cache()
            print(f"\n🌙 [Scheduler] Dispatching Tier 3 Final Night Reminder ({now_ist.strftime('%I:%M %p IST')})...")
            email_dispatcher.send_questionnaire_email("night", date_str)
            db.mark_reminder_sent("night", date_str)

    async def poll_inbound_emails(self):
        """Polls unread inbox for '[Harvester Run Config]' replies every 2 minutes."""
        incoming = imap_reader.check_incoming_responses()
        if not incoming:
            return

        for inc in incoming:
            sender = inc["sender"]
            subject = inc["subject"]
            body = inc["body"]
            print(f"📥 [IMAP Listener] Detected inbound config from '{sender}': '{subject}'")

            parsed_config, errors = parse_run_config_tags(body)
            if errors:
                print(f"⚠️ [IMAP Listener] Validation errors in email from '{sender}': {errors}")
                email_dispatcher.send_corrective_email(sender, errors, body, date_str=date_str)
            else:
                print(f"✅ [IMAP Listener] Valid configuration accepted from '{sender}'.")
                # Trigger async harvesting & verification pipeline
                asyncio.create_task(execute_email_triggered_pipeline(parsed_config, sender))

    async def run_daemon(self, poll_interval_seconds: Optional[int] = None):
        """Runs the background scheduler and 2-minute IMAP polling daemon continuously."""
        poll_interval = poll_interval_seconds or cfg.IMAP_POLL_INTERVAL_SECONDS
        self.running = True
        print(f"\n⏰ [Scheduler Daemon] Started.")
        print(f"  • Reminders : 07:30 AM, 02:00 PM, 09:00 PM IST")
        print(f"  • IMAP Poll : Every {poll_interval}s for '[Harvester Run Config]'")
        print(f"  • Daily Flag: SQLite persistent (Midnight 00:00 IST reset)\n")

        # Initial cache cleanup on scheduler boot
        purge_stale_cache()

        loop_counter = 0
        while self.running:
            try:
                # Check scheduled reminders
                self.check_and_dispatch()

                # Poll IMAP inbox
                await self.poll_inbound_emails()

            except Exception as e:
                logger.error(f"[Scheduler Loop Exception] {e}")

            loop_counter += 1
            await asyncio.sleep(poll_interval)


scheduler = ThreeTierScheduler()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-now":
        tier = sys.argv[2] if len(sys.argv) > 2 else None
        scheduler.check_and_dispatch(force_tier=tier)
    else:
        asyncio.run(scheduler.run_daemon())
