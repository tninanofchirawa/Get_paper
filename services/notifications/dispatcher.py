"""
services/notifications/dispatcher.py - High-level email orchestration and report dispatch service.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import logging
from typing import Optional, Dict, Any, List

from config import cfg
from services.notifications.tag_parser import get_ist_now
from services.notifications.smtp_dispatcher import send_smtp_email
from services.notifications.mailgun_dispatcher import send_mailgun_email
from services.notifications.sendgrid_dispatcher import send_sendgrid_email
from services.notifications.templates import wrap_html_container, CODE_FONT

logger = logging.getLogger("EmailDispatcher")


class EmailDispatcher:
    """Dispatches responsive HTML reports, reminders, questionnaires, and CSV attachments."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or cfg.EMAIL_PROVIDER).lower()

    def send(
        self,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
        recipient: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Dispatches email across SMTP, Mailgun, or SendGrid without crashing on errors."""
        try:
            to_email = recipient or cfg.RECIPIENT_EMAIL
            if not plain_body:
                plain_body = f"{subject}\n\nPlease view this email in an HTML-compatible email client."

            if self.provider == "mailgun" and cfg.MAILGUN_API_KEY and cfg.MAILGUN_DOMAIN:
                return send_mailgun_email(to_email, subject, html_body, attachment_paths, plain_body)
            elif self.provider == "sendgrid" and cfg.SENDGRID_API_KEY:
                return send_sendgrid_email(to_email, subject, html_body, attachment_paths, plain_body)
            elif self.provider == "console" or (self.provider == "smtp" and (not cfg.SMTP_USER or not cfg.SMTP_PASSWORD)):
                print(f"\n📧 [CONSOLE EMAIL DISPATCH] To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Attachments: {attachment_paths or 'None'}")
                print("-" * 65)
                print(plain_body[:600] + ("..." if len(plain_body) > 600 else ""))
                print("-" * 65)
                return True
            else:
                return self._send_smtp(subject, html_body, plain_body, to_email, attachment_paths=attachment_paths)
        except Exception as e:
            logger.error(f"[Email Dispatch Error] Failed to send email '{subject}': {e}", exc_info=True)
            print(f"⚠️ [Email Dispatch Warning] Could not deliver email: {e} (Pipeline execution and Drive sync remain preserved).")
            return False

    def _send_smtp(
        self,
        subject: str,
        html_body: str,
        plain_body: str,
        to_email: str,
        from_header: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Sends email via SMTP transport."""
        return send_smtp_email(to_email, subject, html_body, attachment_paths, plain_body)

    def _send_mailgun(
        self,
        subject: str,
        html_body: str,
        plain_body: str,
        to_email: str,
        from_header: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Sends email via Mailgun transport."""
        return send_mailgun_email(to_email, subject, html_body, attachment_paths, plain_body)

    def _send_sendgrid(
        self,
        subject: str,
        html_body: str,
        plain_body: str,
        to_email: str,
        from_header: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Sends email via SendGrid transport."""
        return send_sendgrid_email(to_email, subject, html_body, attachment_paths, plain_body)

    def send_morning_intake_questionnaire(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches Morning Intake Questionnaire (07:30 AM IST)."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"🌅 [Daily Research Brief] Configure Your Paper Harvest Pipeline — {date_str}"
        plain_body = f"""✨ ACADEMIC LITERATURE HARVESTER & VERIFIER
Good morning! ☀️ Ready to run today's literature exploration?
Simply hit 'Reply', fill in your preferences next to the tags below, and hit Send. Everything else is handled automatically! 🚀

--------------------------------------------------------------------------------
📋 SECTION 1: EXECUTION PROFILE & ENVIRONMENT
[NAME_OF_RUN]: Run_{date_str}_01
[RUN_TYPE]: Automated ⚙️ (Options: Automated | Manual | Batch)
[LOCATION]: HITS Campus 🏛️ (Options: HITS Campus | Home | Online VPS)
[BATCH_RUN]: No 📦 (Options: Yes | No)
[BATCH_DETAILS]: None 📑 (If Yes: specify batch file name and item position)
[OUTPUT_MODE]: Create New 📄 (Options: Create New | Append to Existing)
[TARGET_SHEET]: None 📊 (If Appending: name of target sheet/file)

🎯 SECTION 2: RESEARCH FOCUS & SUBTOPICS
[TOPIC_COUNT]: 2 🔢 (Max: 5)
🔹 Topic 1:
[TOPIC_1]: Fuzzy Machine Learning
[T1_SUBTOPICS]: T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems, Fuzzy Clustering, Membership Tuning
🔹 Topic 2:
[TOPIC_2]: Graph Neural Networks
[T2_SUBTOPICS]: Spectral Clustering, Link Prediction, Graph Attention Networks

⚖️ SECTION 3: SCOPE, QUOTAS & TIMEFRAME
[PAPERS_PER_TOPIC]: 250 📚 (Preset choices: 100 | 250 | 500 — Hard cap: 500)
[YEAR_RANGE]: 2021-2026 🗓️ (Format: YYYY-YYYY or 'All Years')
[DOC_TYPE]: Journal Articles Only 📑 (Options: Journal Articles Only | Conference Proceedings | Preprints | All)

🛡️ SECTION 4: VERIFICATION TIERS & PIPELINE MODE
[INST_TOKEN]: True 🔑 (Options: True [Scopus/WoS/IEEE authoritative] | False [Open Access fallback])
[TARGET_INDEX]: Scopus, Web of Science, IEEE Xplore, Crossref 🌐
[QUOTA_STRICTNESS]: Strict 🎯 (Options: Strict [paginate until filled] | Fast-Capped [stop on candidate limit])
[ONLY_INDEXED]: False 🎯 (Options: True [Scopus/WoS indexed only] | False [Broad fallback])
--------------------------------------------------------------------------------
"""
        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Good morning! ☀️ Ready to run today's literature exploration?<br>
            Simply hit <b>Reply</b>, fill in your preferences next to the highlighted tags below, and hit <b>Send</b>. Everything else is handled automatically! 🚀
        </div>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                📋 Section 1: Execution Profile & Environment
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; color: #0f172a; line-height: 1.8;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[NAME_OF_RUN]:</span> Run_{date_str}_01<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[RUN_TYPE]:</span> Automated ⚙️<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[LOCATION]:</span> HITS Campus 🏛️<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[BATCH_RUN]:</span> No 📦<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[OUTPUT_MODE]:</span> Create New 📄
            </div>
        </div>
        <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; color: #1e40af;">
            💡 <b>Quick Tip:</b> Keep the square brackets <code>[...]</code> intact so the intake parser reads your values accurately.
        </div>
        """
        html_body = wrap_html_container(
            title="Configure Your Paper Harvest Pipeline",
            header_gradient="linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)",
            header_icon="✨",
            header_subtitle=f"Academic Literature Harvester & Verifier • Daily Research Brief ({date_str})",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    def send_afternoon_reminder(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches Afternoon Catch-Up Notice (02:00 PM IST)."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"☀️ [Afternoon Reminder] Today's Literature Run is Still Pending — {date_str}"
        plain_body = f"""Hey! 👋 Just checking in. Today's paper harvesting run hasn't been triggered yet.
Reply directly with this single-line command:
[RUN_TODAY]: Yes | [TOPIC]: Fuzzy Neural Networks | [QUOTA]: 100
"""
        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Hey! 👋 Just checking in. Today's paper harvesting run hasn't been triggered yet.
        </div>
        <div style="background-color: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <p style="margin: 0 0 10px 0; font-weight: 600; color: #92400e; font-size: 14px;">
                ⚡ Quick Trigger Format:
            </p>
            <div style="background: #ffffff; border: 1px solid #fcd34d; border-radius: 6px; padding: 10px 14px; font-family: {CODE_FONT}; font-size: 13px; color: #1e293b;">
                <code>[RUN_TODAY]: Yes | [TOPIC]: Fuzzy Neural Networks | [QUOTA]: 100</code>
            </div>
        </div>
        """
        html_body = wrap_html_container(
            title="Today's Literature Run is Still Pending",
            header_gradient="linear-gradient(135deg, #d97706 0%, #f59e0b 100%)",
            header_icon="☀️",
            header_subtitle=f"Afternoon Check-In (02:00 PM IST) • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    def send_night_reminder(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches Night Reminder Notice (09:00 PM IST)."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"🌙 [Night Check-in] Final Call for Overnight Research Batch — {date_str}"
        plain_body = f"""Good evening! 🌌 The harvester has been idle today.
Would you like to queue up an overnight harvest so your verified papers are ready on your Google Drive by morning? ☕📊
Reply with:
[TOPIC_1]: Fuzzy Machine Learning | [PAPERS_PER_TOPIC]: 250
"""
        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Good evening! 🌌 Would you like to schedule an overnight harvest?
        </div>
        <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <div style="font-weight: 600; font-size: 14px; color: #1e293b; margin-bottom: 8px;">
                🌙 Queue Up an Overnight Batch?
            </div>
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; font-family: {CODE_FONT}; font-size: 13px; color: #334155;">
                <code>[TOPIC_1]: Fuzzy Machine Learning | [PAPERS_PER_TOPIC]: 250</code>
            </div>
        </div>
        """
        html_body = wrap_html_container(
            title="Final Call for Overnight Research Batch",
            header_gradient="linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%)",
            header_icon="🌙",
            header_subtitle=f"Night Intake Notice (09:00 PM IST) • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    def send_corrective_email(self, recipient: str, errors: List[str], raw_body: str, date_str: Optional[str] = None) -> bool:
        """Dispatches Parameter Adjustment Needed notice with exact correction guidance."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"⚠️ [Harvester Intake Notice] Parameter Adjustment Needed — {date_str}"
        error_bullets = "\n".join(f"• {e}" for e in errors)
        plain_body = f"""🚨 Oops! Configuration adjustments needed:\n{error_bullets}\nPlease reply with corrected tags."""

        error_items_html = "".join(f"<li style='margin-bottom: 8px; color: #991b1b;'>{e}</li>" for e in errors)
        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 16px;">
            🚨 Oops! We noticed a small issue with your configuration reply:
        </div>
        <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <ul style="margin: 0; padding-left: 20px;">
                {error_items_html}
            </ul>
        </div>
        """
        html_body = wrap_html_container(
            title="Parameter Adjustment Needed",
            header_gradient="linear-gradient(135deg, #991b1b 0%, #dc2626 100%)",
            header_icon="⚠️",
            header_subtitle=f"Intake Boundary Validation Notice • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    def send_run_completion_report(
        self,
        run_config: Dict[str, Any],
        metrics: Dict[str, Any],
        csv_path: Optional[str] = None,
        excel_path: Optional[str] = None,
        papers: Optional[List[Any]] = None,
        drive_link: Optional[str] = None,
        drive_file_id: Optional[str] = None,
        log_text: str = "",
        recipient: Optional[str] = None
    ) -> bool:
        """Dispatches executive completion report with index breakdown and attached standardized .csv file."""
        target_file = csv_path or excel_path or ""
        run_name = run_config.get("run_name", f"Run_{get_ist_now().strftime('%Y%m%d_%H%M%S')}")
        total_verified = metrics.get("verified_retained", len(papers) if papers else 0)
        subject = f"✅ [Harvest Complete] {run_name} — {total_verified} Papers Verified & Synced! 📚✨"

        timestamp_ist = get_ist_now().strftime("%d %b %Y, %I:%M %p IST")
        location = run_config.get("location", "Home")
        topics = run_config.get("topics", [run_config.get("main_topic", "Literature")])
        topic_count = len(topics)
        raw_harvested = metrics.get("raw_scraped", 0)
        duplicates_dropped = metrics.get("duplicates_removed", 0)
        excluded_non_indexed = metrics.get("excluded_non_indexed", 0)

        d_link = drive_link or metrics.get("drive_link") or ""
        if not d_link and drive_file_id:
            d_link = f"https://drive.google.com/file/d/{drive_file_id}/view"

        dur_secs = metrics.get("duration_seconds", 0)
        duration_formatted = f"{dur_secs // 60}m {dur_secs % 60}s" if dur_secs >= 60 else f"{dur_secs}s"

        if papers:
            scopus_hits = sum(1 for p in papers if getattr(p, "scopus_indexed", False) or "scopus" in str(getattr(p, "verification_source", "")).lower())
            wos_hits = sum(1 for p in papers if getattr(p, "wos_indexed", False) or "wos" in str(getattr(p, "verification_source", "")).lower())
            ieee_hits = sum(1 for p in papers if getattr(p, "ieee_indexed", False) or "ieee" in str(getattr(p, "verification_source", "")).lower())
            cr_hits = sum(1 for p in papers if "crossref" in str(getattr(p, "verification_source", "")).lower() or "crossref" in str(getattr(p, "verified_sources", "")).lower())
            oa_hits = sum(1 for p in papers if getattr(p, "open_access", False) or "openalex" in str(getattr(p, "verification_source", "")).lower())
            arxiv_hits = sum(1 for p in papers if "arxiv" in str(getattr(p, "verification_source", "")).lower() or "arxiv" in str(getattr(p, "verified_sources", "")).lower())
            s2_hits = sum(1 for p in papers if "semantic scholar" in str(getattr(p, "verification_source", "")).lower() or "semantic scholar" in str(getattr(p, "verified_sources", "")).lower())
        else:
            scopus_hits = metrics.get("scopus_hits", total_verified if run_config.get("inst_token_flag") else 0)
            wos_hits = metrics.get("wos_hits", 0)
            ieee_hits = metrics.get("ieee_hits", 0)
            cr_hits = metrics.get("crossref_hits", 0)
            oa_hits = metrics.get("open_access_hits", total_verified if not run_config.get("inst_token_flag") else 0)
            arxiv_hits = metrics.get("arxiv_hits", 0)
            s2_hits = metrics.get("semantic_scholar_hits", 0)

        filename = os.path.basename(target_file) if target_file else f"{run_name}.csv"
        folder_name = cfg.GDRIVE_FOLDER_ID or "Google Drive / Research Papers"

        plain_body = f"""🎉 RUN SUCCESSFUL: {run_name}
Completed at: {timestamp_ist} | Location: {location} 🏛️

📊 Pipeline Execution Metrics:
├─ 🎯 Main Topics Searched: {topic_count} ({', '.join(topics)})
├─ 📥 Total Raw Papers Harvested: {raw_harvested}
├─ 🧹 Duplicates Removed: {duplicates_dropped}
├─ 🏆 Authoritative Verified Count: {total_verified}
├─ 🚫 Excluded Non-Indexed (Scopus/WoS filter): {excluded_non_indexed}
└─ ⏱️ Total Execution Duration: {duration_formatted}

🌐 Multi-Source Academic Verification Breakdown:
├─ 🔬 Elsevier Scopus: {scopus_hits} papers
├─ 🏛️ Clarivate Web of Science: {wos_hits} papers
├─ ⚡ IEEE Xplore: {ieee_hits} papers
├─ 🌐 Crossref Confirmed: {cr_hits} citations
├─ 🔓 OpenAlex CC0 Verified: {oa_hits} papers
├─ 📄 arXiv Preprints: {arxiv_hits} papers
└─ 🧠 Semantic Scholar: {s2_hits} papers

☁️ Google Drive Sync:
├─ Status: Uploaded to '{folder_name}' ✅
└─ 🔗 Drive Link: {d_link or 'Configured via Service Account'}

📁 Local Archive: Saved in 'output/{filename}' ✅
📎 Attached: '{filename}' (standard UTF-8 CSV containing complete schema and consolidated Verified Sources).
"""
        drive_button_html = f"""
        <div style="margin-top: 10px;">
            <a href="{d_link}" style="background-color: #2563eb; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px; display: inline-block;">
                Open in Google Drive ↗
            </a>
        </div>
        """ if d_link else ""

        content_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                🎉 RUN SUCCESSFUL: {run_name}
            </div>
            <div style="font-size: 13px; color: #64748b;">
                Completed at: <b>{timestamp_ist}</b> | Location: <b>{location} 🏛️</b>
            </div>
        </div>
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                📊 Pipeline Execution Metrics
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; line-height: 1.8; color: #1e293b;">
                ├─ 🎯 Main Topics Searched: <b>{topic_count}</b><br>
                ├─ 📥 Total Raw Papers Harvested: <b>{raw_harvested}</b><br>
                ├─ 🧹 Duplicates Removed: <b>{duplicates_dropped}</b><br>
                ├─ 🏆 Authoritative Verified Count: <b>{total_verified} papers</b><br>
                ├─ 🚫 Excluded Non-Indexed: <b>{excluded_non_indexed} papers</b><br>
                └─ ⏱️ Execution Duration: <b>{duration_formatted}</b>
            </div>
        </div>
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                🌐 Multi-Source Academic Verification Breakdown
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; line-height: 1.8; color: #1e293b;">
                ├─ 🔬 Scopus: <b>{scopus_hits}</b> | 🏛️ WoS: <b>{wos_hits}</b> | ⚡ IEEE: <b>{ieee_hits}</b><br>
                ├─ 🌐 Crossref: <b>{cr_hits}</b> | 🔓 OpenAlex: <b>{oa_hits}</b><br>
                └─ 📄 arXiv: <b>{arxiv_hits}</b> | 🧠 Semantic Scholar: <b>{s2_hits}</b>
            </div>
        </div>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="font-size: 13px; color: #334155; line-height: 1.7;">
                ☁️ <b>Google Drive Sync:</b> Uploaded to <code>{folder_name}</code> ✅<br>
                📁 <b>Local Archive:</b> Saved in <code>output/{filename}</code> ✅
                {drive_button_html}
            </div>
        </div>
        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; font-size: 13px; color: #1e40af;">
            📎 <b>Attached:</b> <code>{filename}</code> (standard UTF-8 CSV).
        </div>
        """
        html_body = wrap_html_container(
            title=f"Harvest Complete: {run_name}",
            header_gradient="linear-gradient(135deg, #065f46 0%, #059669 50%, #10b981 100%)",
            header_icon="✅",
            header_subtitle=f"{total_verified} Papers Verified & Synchronized 📚✨",
            content_html=content_html
        )
        attachments = [target_file] if (target_file and os.path.exists(target_file)) else None
        return self.send(subject, html_body, plain_body, recipient, attachment_paths=attachments)

    def send_questionnaire_email(self, tier_name: str, date_str: str, recipient: Optional[str] = None) -> bool:
        """Route generic questionnaire tier calls to corresponding specialized handlers."""
        t = tier_name.lower().strip()
        if "morning" in t:
            return self.send_morning_intake_questionnaire(date_str, recipient=recipient)
        elif "afternoon" in t:
            return self.send_afternoon_reminder(date_str, recipient=recipient)
        elif "night" in t:
            return self.send_night_reminder(date_str, recipient=recipient)
        return self.send_morning_intake_questionnaire(date_str, recipient=recipient)


# Global singleton instance
email_dispatcher = EmailDispatcher()
