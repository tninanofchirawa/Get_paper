"""
email_service.py - 100% Free Gmail SMTP dispatcher and IMAP inbound configuration listener.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import re
import sys
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import Optional, List, Dict, Any, Tuple

from config import cfg

logger = logging.getLogger("EmailService")

# ==============================================================================
# 1. QUESTIONNAIRE TEMPLATE & TAG REGEX PARSER
# ==============================================================================

CONFIG_TAG_PATTERN = re.compile(
    r"\[(?P<tag>[A-Z0-9_]+)\]\s*[:=\-]?\s*(?P<val>[^\r\n\[]*)",
    re.IGNORECASE
)


def get_default_questionnaire_template(run_name: str = "Morning_Harvest_Auto") -> str:
    """Returns the formatted 15-tag template ready for user replies."""
    return f"""[NAME_OF_RUN] {run_name}
[RUN_TYPE] Automated
[LOCATION] Home
[BATCH_RUN] No
[BATCH_DETAILS] None
[OUTPUT_MODE] Create New Excel
[TARGET_SHEET] Verified Papers
[TOPIC_COUNT] 1
[TOPIC_1] Fuzzy Logic and Deep Neural Networks
[TOPIC_2] 
[TOPIC_3] 
[TOPIC_4] 
[TOPIC_5] 
[T1_SUBTOPICS] Neuro-Fuzzy Systems, ANFIS, Explainable AI, Takagi-Sugeno
[T2_SUBTOPICS] 
[T3_SUBTOPICS] 
[T4_SUBTOPICS] 
[T5_SUBTOPICS] 
[PAPERS_PER_TOPIC] 250
[YEAR_RANGE] 2021-2026
[DOC_TYPE] Journal Articles
[INST_TOKEN] False
[TARGET_INDEX] Scopus, Web of Science, IEEE Xplore, Crossref, OpenAlex
[QUOTA_STRICTNESS] Strict"""


def parse_run_config_tags(body: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Parses the 15 configuration tags from an email reply using regex.
    Enforces strict caps:
      - Max 5 topics
      - Max 5 subtopics each
      - Max 500 papers per topic

    Returns:
      Tuple[Optional[Dict[str, Any]], List[str]]: (parsed_config, error_list)
    """
    errors: List[str] = []
    tags: Dict[str, str] = {}

    for match in CONFIG_TAG_PATTERN.finditer(body):
        tag_name = match.group("tag").strip().upper()
        tag_val = match.group("val").strip()
        tags[tag_name] = tag_val

    if not tags:
        return None, ["No configuration tags (e.g., [NAME_OF_RUN], [TOPIC_1]) were detected in your email body."]

    # 1. Run Name & General
    run_name = tags.get("NAME_OF_RUN") or f"Run_{datetime_now_str()}"
    run_type = tags.get("RUN_TYPE") or "Automated"
    location = tags.get("LOCATION") or "Home"

    # 2. Batch Run
    batch_str = tags.get("BATCH_RUN", "No").lower()
    is_batch = batch_str in ("yes", "y", "true", "1")
    batch_details = tags.get("BATCH_DETAILS") or "None"

    # 3. Output mode & target sheet
    output_mode = tags.get("OUTPUT_MODE") or "Create New Excel"
    target_sheet = tags.get("TARGET_SHEET") or "Verified Papers"

    # 4. Topics & Subtopics
    topics: List[str] = []
    subtopics_map: Dict[str, List[str]] = {}

    for i in range(1, 6):
        top_val = tags.get(f"TOPIC_{i}", "").strip()
        if top_val and top_val.lower() not in ("none", "null", "n/a", "-"):
            topics.append(top_val)
            sub_raw = tags.get(f"T{i}_SUBTOPICS", "").strip()
            if sub_raw and sub_raw.lower() not in ("none", "null", "n/a", "-"):
                subs = [s.strip() for s in re.split(r"[,;]+", sub_raw) if s.strip()]
                # Cap at 5 subtopics
                subtopics_map[top_val] = subs[:cfg.HARD_CAP_SUBTOPICS_PER_TOPIC]
            else:
                subtopics_map[top_val] = []

    # Enforce topic cap
    topics = topics[:cfg.HARD_CAP_TOPICS]

    # Validate topic availability if not batch
    if not is_batch and not topics:
        errors.append("At least one target topic ([TOPIC_1]) must be provided when [BATCH_RUN] is No.")

    # 5. Papers per topic (Cap at 500)
    quota_raw = tags.get("PAPERS_PER_TOPIC", str(cfg.DEFAULT_QUOTA)).strip()
    try:
        quota = int(re.sub(r"[^\d]", "", quota_raw)) if quota_raw else cfg.DEFAULT_QUOTA
        if quota < 1:
            quota = cfg.DEFAULT_QUOTA
        elif quota > cfg.HARD_CAP_QUOTA_PER_TOPIC:
            logger.info(f"[Config Parser] Capping requested quota {quota} to hard-cap {cfg.HARD_CAP_QUOTA_PER_TOPIC}.")
            quota = cfg.HARD_CAP_QUOTA_PER_TOPIC
    except Exception:
        quota = cfg.DEFAULT_QUOTA

    # 6. Year Range
    year_range = tags.get("YEAR_RANGE") or "All Years"

    # 7. Doc Type
    doc_type = tags.get("DOC_TYPE") or "All"

    # 8. Institutional Token
    inst_token_str = tags.get("INST_TOKEN", "False").lower()
    inst_token = inst_token_str in ("true", "yes", "y", "1")

    # 9. Target Repositories
    target_idx_raw = tags.get("TARGET_INDEX") or "Scopus, Web of Science, IEEE Xplore, Crossref, OpenAlex"
    target_repos = [r.strip() for r in re.split(r"[,;]+", target_idx_raw) if r.strip()]

    # 10. Quota Strictness
    quota_strictness = tags.get("QUOTA_STRICTNESS") or "Strict"
    if "fast" in quota_strictness.lower() or "capped" in quota_strictness.lower():
        quota_strictness = "Fast-Capped"
    else:
        quota_strictness = "Strict"

    if errors:
        return None, errors

    config = {
        "run_name": run_name,
        "run_type": run_type,
        "location": location,
        "is_batch": is_batch,
        "batch_details": batch_details,
        "output_mode": output_mode,
        "target_sheet": target_sheet,
        "topic_count": len(topics),
        "topics": topics,
        "subtopics_map": subtopics_map,
        "main_topic": topics[0] if topics else "Batch Collection",
        "subtopics": subtopics_map.get(topics[0], []) if topics else [],
        "harvest_quota": quota,
        "year_range": year_range,
        "doc_filter": doc_type,
        "inst_token_flag": inst_token,
        "target_repos": target_repos,
        "quota_strictness": quota_strictness,
        "raw_tags": tags
    }
    return config, []


def datetime_now_str() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


# ==============================================================================
# 2. EMAIL DISPATCHER (100% Free Gmail SMTP)
# ==============================================================================
class EmailDispatcher:
    """Dispatches responsive HTML reports, reminders, questionnaires, and Excel attachments via SMTP."""

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
        """Dispatches email with optional file attachments."""
        to_email = recipient or cfg.RECIPIENT_EMAIL
        from_email = cfg.SMTP_USER or "pipeline@academic-harvester.org"
        from_header = f"{cfg.EMAIL_SENDER_NAME} <{from_email}>"

        if not plain_body:
            plain_body = f"{subject}\n\nPlease view this message in an HTML-compatible email client."

        # Console fallback if credentials are empty or provider is console
        if self.provider == "console" or not cfg.SMTP_USER or not cfg.SMTP_PASSWORD:
            print(f"\n📧 [CONSOLE EMAIL DISPATCH] To: {to_email} | Subject: {subject}")
            print(f"Attachments: {attachment_paths or 'None'}")
            print("-" * 50)
            print(plain_body[:500] + ("..." if len(plain_body) > 500 else ""))
            print("-" * 50)
            return True

        return self._send_smtp(subject, html_body, plain_body, to_email, from_header, attachment_paths)

    def _send_smtp(
        self,
        subject: str,
        html_body: str,
        plain_body: str,
        to_email: str,
        from_header: str,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Sends email via Gmail SMTP with STARTTLS and MIME attachments."""
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = to_email

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(plain_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        if attachment_paths:
            for path in attachment_paths:
                if path and os.path.exists(path):
                    try:
                        filename = os.path.basename(path)
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                        msg.attach(part)
                    except Exception as e:
                        logger.warning(f"Could not attach '{path}': {e}")

        try:
            with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=25) as server:
                server.ehlo()
                if cfg.SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                server.sendmail(cfg.SMTP_USER, [to_email], msg.as_string())
            logger.info(f"Email successfully delivered to {to_email}.")
            print(f"📨 [Email OK] Delivered to {to_email}: '{subject}'")
            return True
        except Exception as e:
            logger.error(f"Failed to deliver SMTP email: {e}")
            print(f"❌ [Email ERROR] SMTP delivery failed: {e}")
            return False

    def send_questionnaire_email(self, tier_name: str, date_str: str) -> bool:
        """Sends morning, afternoon, or night questionnaire prompt with 15 tags."""
        run_name = f"Run_{date_str.replace('-', '')}"
        template = get_default_questionnaire_template(run_name)

        subject = f"[Harvester Run Config] {tier_name.capitalize()} Research Intake - {date_str}"
        plain_body = f"""Good day! 🎓

Please REPLY to this email (keeping '[Harvester Run Config]' in the subject) with your run parameters:

--------------------------------------------------------------------------------
{template}
--------------------------------------------------------------------------------

The autonomous pipeline will immediately parse your reply, harvest candidates, verify them across Scopus/WoS/IEEE, and deliver your Excel report! 🚀
"""

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; padding: 20px;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="background: linear-gradient(135deg, #1F4E78 0%, #2B6CB0 100%); color: #FFFFFF; padding: 24px;">
                    <h2 style="margin: 0; font-size: 22px;">🌅 {tier_name.capitalize()} Research Intake Questionnaire</h2>
                    <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Academic Harvester & Dual-Branch Verifier Pipeline ({date_str})</p>
                </div>
                <div style="padding: 24px;">
                    <p style="font-size: 15px;">Please <b>Reply</b> directly to this email to trigger today's literature harvesting & verification. You can customize the parameters in the template below:</p>
                    <div style="background: #F8FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 16px; margin: 16px 0;">
                        <pre style="margin: 0; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: #1A202C; white-space: pre-wrap;">{template}</pre>
                    </div>
                    <p style="font-size: 13px; color: #718096;">⚡ <b>Tip:</b> Keep <code>[Harvester Run Config]</code> in your subject line. The system automatically polls the inbox and starts processing upon receipt.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(subject, html_body, plain_body)

    def send_corrective_email(self, recipient: str, errors: List[str], raw_body: str) -> bool:
        """Sends a corrective email reply when incoming tags are malformed or missing."""
        subject = "[CORRECTION NEEDED] [Harvester Run Config] Invalid Configuration Submitted"
        error_bullets = "\n".join(f"• {e}" for e in errors)
        template = get_default_questionnaire_template()

        plain_body = f"""Hello! ⚠️

We received your research intake email, but the following configuration errors were detected:

{error_bullets}

Please reply with the corrected tags below:
--------------------------------------------------------------------------------
{template}
--------------------------------------------------------------------------------
"""
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
            <div style="background-color: #C53030; color: #fff; padding: 16px; border-radius: 6px;">
                <h3 style="margin:0;">⚠️ Configuration Correction Required</h3>
            </div>
            <div style="padding: 16px; border: 1px solid #FED7D7; margin-top: 10px; border-radius: 6px; background-color: #FFF5F5;">
                <p>We could not launch your paper harvest because of the following issues:</p>
                <ul>
                    {''.join(f'<li style="color: #9B2C2C;"><b>{e}</b></li>' for e in errors)}
                </ul>
                <p>Please reply to this email with the corrected 15-tag template:</p>
                <pre style="background: #FFF; border: 1px solid #CBD5E0; padding: 12px; border-radius: 4px;">{template}</pre>
            </div>
        </body>
        </html>
        """
        return self.send(subject, html_body, plain_body, recipient=recipient)

    def send_run_completion_report(
        self,
        run_config: Dict[str, Any],
        metrics: Dict[str, int],
        excel_path: str,
        log_text: str = "",
        recipient: Optional[str] = None
    ) -> bool:
        """Sends completion report with metrics, execution log, and Excel attachment."""
        run_name = run_config.get("run_name", "Harvesting_Run")
        subject = f"✅ [COMPLETED] Academic Harvester Report - {run_name}"

        raw_cnt = metrics.get("raw_scraped", 0)
        dup_cnt = metrics.get("duplicates_removed", 0)
        ret_cnt = metrics.get("verified_retained", 0)
        duration_sec = metrics.get("duration_seconds", 0)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background: #F7FAFC; padding: 20px;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden;">
                <div style="background: #1F4E78; color: #fff; padding: 20px;">
                    <h2 style="margin: 0;">🎉 Academic Harvester & Verifier Run Complete</h2>
                    <p style="margin: 4px 0 0 0; opacity: 0.9;">Run: <b>{run_name}</b></p>
                </div>
                <div style="padding: 20px;">
                    <h3>📊 Execution Metrics:</h3>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Main Topic:</b></td><td>{run_config.get('main_topic', 'N/A')}</td></tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Target Quota:</b></td><td>{run_config.get('harvest_quota', cfg.DEFAULT_QUOTA)}</td></tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Raw Candidates Scraped:</b></td><td>{raw_cnt}</td></tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Duplicates Removed:</b></td><td>{dup_cnt}</td></tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Verified Papers Retained:</b></td><td style="color: #28a745; font-weight: bold; font-size: 16px;">{ret_cnt}</td></tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;"><td style="padding: 8px 0;"><b>Execution Duration:</b></td><td>{duration_sec}s</td></tr>
                    </table>
                    <p>The standardized research database is attached as <b>{os.path.basename(excel_path)}</b>.</p>
                    {f'<h4>Execution Log:</h4><pre style="background: #F8FAFC; padding: 12px; border-radius: 4px; font-size: 12px; border: 1px solid #E2E8F0;">{log_text}</pre>' if log_text else ''}
                </div>
            </div>
        </body>
        </html>
        """
        plain_body = f"""Academic Paper Harvester & Verifier Run Complete: {run_name}
================================================================================
• Main Topic                : {run_config.get('main_topic', 'N/A')}
• Target Quota              : {run_config.get('harvest_quota', cfg.DEFAULT_QUOTA)}
• Total Raw Scraped         : {raw_cnt}
• Total Duplicates Removed  : {dup_cnt}
• Final Verified Retained   : {ret_cnt}
• Output Excel File Attached: {os.path.basename(excel_path)}
"""
        return self.send(subject, html_body, plain_body, recipient, attachment_paths=[excel_path])


# ==============================================================================
# 3. IMAP INBOUND CONFIGURATION LISTENER
# ==============================================================================
class IMAPQuestionnaireReader:
    """Polls email inbox via IMAP to read incoming questionnaire answers."""

    def __init__(self):
        self.host = cfg.IMAP_HOST
        self.port = cfg.IMAP_PORT
        self.user = cfg.IMAP_USER
        self.password = cfg.IMAP_PASSWORD
        self.use_ssl = cfg.IMAP_USE_SSL

    def check_incoming_responses(self) -> List[Dict[str, Any]]:
        """
        Polls unread inbox for emails containing '[Harvester Run Config]' in the subject.
        Returns list of message dicts: {'sender', 'subject', 'body', 'uid'}.
        """
        if not self.user or not self.password:
            return []

        matching_messages = []
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port) if self.use_ssl else imaplib.IMAP4(self.host, self.port)
            mail.login(self.user, self.password)
            mail.select("inbox")

            status, data = mail.search(None, '(UNSEEN)')
            if status != "OK" or not data or not data[0]:
                return []

            for num in data[0].split():
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender = msg.get("From", "")
                        subject = msg.get("Subject", "")

                        # Filter strictly for Harvester Run Config subject tag
                        if "[Harvester Run Config]" not in subject:
                            continue

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                if ctype == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                                elif ctype == "text/html" and not body:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                        matching_messages.append({
                            "msg_id": num.decode("utf-8"),
                            "sender": sender,
                            "subject": subject,
                            "body": body.strip()
                        })

                        # Mark as read/seen so it's not processed repeatedly
                        mail.store(num, "+FLAGS", "\\Seen")

        except Exception as e:
            logger.warning(f"IMAP poll error: {e}")
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

        return matching_messages


# Global service instances
email_dispatcher = EmailDispatcher()
imap_reader = IMAPQuestionnaireReader()
