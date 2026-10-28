"""
email_service.py - Richly styled multi-part MIME email dispatcher and resilient IMAP inbound listener.
Unified Academic Paper Harvester, Verifier & 100% Gmail-Driven Notification Pipeline.
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
import datetime
from datetime import timezone, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple

from config import cfg

logger = logging.getLogger("EmailService")

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


def get_ist_now() -> datetime.datetime:
    """Returns current timestamp in Indian Standard Time (IST, UTC+5:30)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_tz)


# ==============================================================================
# 1. QUESTIONNAIRE TEMPLATE GENERATORS
# ==============================================================================

def get_morning_questionnaire_template(date_str: Optional[str] = None) -> str:
    """
    Returns the standard Section 2 15-tag Morning Intake Questionnaire text.
    Preserves exact tags and formatting for copy-pasting or direct mobile reply.
    """
    if not date_str:
        date_str = get_ist_now().strftime("%Y-%m-%d")

    return f"""[NAME_OF_RUN]: Run_{date_str}_01
[RUN_TYPE]: Automated ⚙️ (Options: Automated | Manual | Batch)
[LOCATION]: HITS Campus 🏛️ (Options: HITS Campus | Home | Online VPS)
[BATCH_RUN]: No 📦 (Options: Yes | No)
[BATCH_DETAILS]: None 📑 (If Yes: specify batch file name and item position)
[OUTPUT_MODE]: Create New 📄 (Options: Create New | Append to Existing)
[TARGET_SHEET]: None 📊 (If Appending: name of target sheet/file)

[TOPIC_COUNT]: 2 🔢 (Max: 5)
[TOPIC_1]: Fuzzy Machine Learning
[T1_SUBTOPICS]: T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems, Fuzzy Clustering, Membership Tuning
[TOPIC_2]: Graph Neural Networks
[T2_SUBTOPICS]: Spectral Clustering, Link Prediction, Graph Attention Networks
[TOPIC_3]: 
[T3_SUBTOPICS]: 
[TOPIC_4]: 
[T4_SUBTOPICS]: 
[TOPIC_5]: 
[T5_SUBTOPICS]: 

[PAPERS_PER_TOPIC]: 250 📚 (Preset choices: 100 | 250 | 500 — Hard cap: 500)
[YEAR_RANGE]: 2021-2026 🗓️ (Format: YYYY-YYYY or 'All Years')
[DOC_TYPE]: Journal Articles Only 📑 (Options: Journal Articles Only | Conference Proceedings | Preprints | All)

[INST_TOKEN]: True 🔑 (Options: True [Scopus/WoS/IEEE authoritative] | False [Open Access fallback])
[TARGET_INDEX]: Scopus, Web of Science, IEEE Xplore, Crossref 🌐
[QUOTA_STRICTNESS]: Strict 🎯 (Options: Strict [paginate until filled] | Fast-Capped [stop on candidate limit])"""


# ==============================================================================
# 2. RESILIENT REGEX CONFIGURATION PARSER
# ==============================================================================

# Resilient regex pattern matching:
# Matches tag [TAG_NAME] on the current line and captures value up to either `| [` (pipe followed by tag) or newline
TAG_REGEX_PATTERN = re.compile(
    r"\[(?P<tag>[A-Z0-9_]+)\][ \t]*[:=\-]?[ \t]*(?P<val>.*?)(?=[ \t]*\|[ \t]*\[|\r|\n|$)",
    re.IGNORECASE
)


def _clean_field_value(raw_val: str) -> str:
    """Strips email reply quote prefixes (>), trailing option helpers in parentheses, and decorative emojis."""
    if not raw_val:
        return ""
    v = raw_val.strip()
    # Strip email quote prefixes like > or >>
    v = re.sub(r"^[>\s]+", "", v).strip()
    # Remove trailing parentheses helper text e.g. (Options: ...), (Preset choices: ...)
    v = re.sub(r"\s*\([^)]*(?:Options|Preset|Format|Max|If Yes|If Appending)[^)]*\)", "", v, flags=re.IGNORECASE).strip()
    # Strip emojis that might be trailing choices
    v = re.sub(r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\ufe0f]", "", v).strip()
    return v


def parse_run_config_tags(body: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Parses configuration tags from an incoming email reply body.
    Supports:
      1. Standard multi-line 15-tag template with colons, options, and emojis.
      2. Quick single-line trigger format: `[RUN_TODAY]: Yes | [TOPIC]: ... | [QUOTA]: 100`.
      3. Strict boundary enforcement (Max 5 topics, Max 5 subtopics each, Max 500 papers).

    Returns:
      Tuple[Optional[Dict[str, Any]], List[str]]: (parsed_config, error_list)
    """
    errors: List[str] = []
    tags: Dict[str, str] = {}

    # Extract tags (matching both multi-line and pipe-separated forms)
    for match in TAG_REGEX_PATTERN.finditer(body):
        tag_name = match.group("tag").strip().upper()
        raw_val = match.group("val")
        cleaned_val = _clean_field_value(raw_val)
        if tag_name not in tags or cleaned_val:
            tags[tag_name] = cleaned_val

    if not tags:
        return None, ["No configuration tags (e.g., [NAME_OF_RUN], [TOPIC_1]) were detected in your email body."]

    # Quick single-line format support: [RUN_TODAY], [TOPIC], [QUOTA]
    if "TOPIC" in tags and "TOPIC_1" not in tags:
        tags["TOPIC_1"] = tags["TOPIC"]
    if "QUOTA" in tags and "PAPERS_PER_TOPIC" not in tags:
        tags["PAPERS_PER_TOPIC"] = tags["QUOTA"]

    # 1. Run Name & Metadata
    date_str = get_ist_now().strftime("%Y%m%d")
    run_name = tags.get("NAME_OF_RUN") or f"Run_{date_str}_01"
    run_type = tags.get("RUN_TYPE") or "Automated"
    location = tags.get("LOCATION") or "Home"

    # 2. Batch Run
    batch_str = tags.get("BATCH_RUN", "No").lower()
    is_batch = batch_str in ("yes", "y", "true", "1")
    batch_details = tags.get("BATCH_DETAILS") or "None"

    # 3. Output mode & target sheet
    output_mode = tags.get("OUTPUT_MODE") or "Create New"
    target_sheet = tags.get("TARGET_SHEET") or "None"

    # 4. Topics & Subtopics
    topics: List[str] = []
    subtopics_map: Dict[str, List[str]] = {}

    max_topics = 5
    if "TOPIC_COUNT" in tags and tags["TOPIC_COUNT"]:
        try:
            req_top_count = int(re.sub(r"[^\d]", "", tags["TOPIC_COUNT"]))
            if req_top_count > 5:
                errors.append(f"❌ [TOPIC_COUNT]: You requested {req_top_count} topics. (Maximum allowed is 5).")
            elif req_top_count > 0:
                max_topics = req_top_count
        except Exception:
            pass

    for i in range(1, 8):  # Check up to 7 to detect user boundary overflow
        top_val = tags.get(f"TOPIC_{i}", "").strip()
        if top_val and top_val.lower() not in ("none", "null", "n/a", "-", ""):
            if i > 5:
                errors.append(f"❌ [TOPIC_{i}]: Topic '{top_val}' exceeds the maximum allowed limit of 5 topics.")
                continue

            if len(topics) < max_topics:
                topics.append(top_val)
                sub_raw = tags.get(f"T{i}_SUBTOPICS", "").strip()
                if sub_raw and sub_raw.lower() not in ("none", "null", "n/a", "-", ""):
                    subs = [s.strip() for s in re.split(r"[,;]+", sub_raw) if s.strip()]
                    if len(subs) > 5:
                        errors.append(f"❌ [T{i}_SUBTOPICS]: You provided {len(subs)} subtopics. (Maximum allowed is 5).")
                    subtopics_map[top_val] = subs[:5]
                else:
                    subtopics_map[top_val] = []

    # Validate at least one topic if not batch run
    if not is_batch and not topics:
        errors.append("❌ [TOPIC_1]: At least one topic must be specified.")

    # 5. Papers per topic boundary check (Hard cap 500)
    quota_raw = tags.get("PAPERS_PER_TOPIC", "250").strip()
    quota = 250
    if quota_raw:
        try:
            num_match = re.search(r"\d+", quota_raw)
            if num_match:
                req_quota = int(num_match.group(0))
                if req_quota > 500:
                    errors.append(
                        f"❌ [PAPERS_PER_TOPIC]: You requested {req_quota} papers. "
                        f"(The hard ceiling is 500 papers per topic to prevent API blocks)."
                    )
                    quota = 500
                elif req_quota < 1:
                    quota = 250
                else:
                    quota = req_quota
        except Exception:
            quota = 250

    # 6. Year range
    year_range = tags.get("YEAR_RANGE") or "All Years"

    # 7. Document type filter
    doc_type = tags.get("DOC_TYPE") or "Journal Articles Only"

    # 8. Institutional token flag
    inst_token_str = tags.get("INST_TOKEN", "True").lower()
    inst_token = inst_token_str in ("true", "yes", "y", "1")

    # 9. Target Repositories
    target_idx_raw = tags.get("TARGET_INDEX") or "Scopus, Web of Science, IEEE Xplore, Crossref"
    target_repos = [r.strip() for r in re.split(r"[,;]+", target_idx_raw) if r.strip()]

    # 10. Quota strictness
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
        "main_topic": topics[0] if topics else "Batch Run",
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


# ==============================================================================
# 3. HTML EMAIL STYLING & GENERATION ENGINE
# ==============================================================================

BASE_EMAIL_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
CODE_FONT = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace"


def _wrap_html_container(title: str, header_gradient: str, header_icon: str, header_subtitle: str, content_html: str) -> str:
    """Wraps body content in a polished, responsive, card-based email layout."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 24px 12px; background-color: #f1f5f9; font-family: {BASE_EMAIL_FONT}; line-height: 1.6; color: #1e293b;">
    <div style="max-width: 660px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <!-- Header -->
        <div style="background: {header_gradient}; color: #ffffff; padding: 28px 24px; text-align: left;">
            <div style="font-size: 24px; font-weight: 700; letter-spacing: -0.5px; margin: 0; display: flex; align-items: center;">
                <span>{header_icon} {title}</span>
            </div>
            <div style="font-size: 14px; opacity: 0.92; margin-top: 6px; font-weight: 400;">
                {header_subtitle}
            </div>
        </div>

        <!-- Main Content -->
        <div style="padding: 24px;">
            {content_html}
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center; font-size: 12px; color: #64748b;">
            Academic Paper Harvester & Verifier • 100% Free Autonomous Research Automation Engine 🎓☕
        </div>
    </div>
</body>
</html>"""


# ==============================================================================
# 4. EMAIL DISPATCHER CLASS
# ==============================================================================

class EmailDispatcher:
    """Dispatches responsive HTML reports, reminders, questionnaires, and Excel attachments via Gmail SMTP."""

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
        """Dispatches multi-part MIME email with HTML and Plain-Text representations."""
        to_email = recipient or cfg.RECIPIENT_EMAIL
        from_email = cfg.SMTP_USER or "pipeline@academic-harvester.org"
        from_header = f"{cfg.EMAIL_SENDER_NAME} <{from_email}>"

        if not plain_body:
            plain_body = f"{subject}\n\nPlease view this email in an HTML-compatible email client."

        # Console fallback if credentials are empty or provider is console
        if self.provider == "console" or not cfg.SMTP_USER or not cfg.SMTP_PASSWORD:
            print(f"\n📧 [CONSOLE EMAIL DISPATCH] To: {to_email}")
            print(f"Subject: {subject}")
            print(f"Attachments: {attachment_paths or 'None'}")
            print("-" * 65)
            print(plain_body[:600] + ("..." if len(plain_body) > 600 else ""))
            print("-" * 65)
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
            logger.info(f"Email successfully delivered to {to_email}: '{subject}'")
            print(f"📨 [Email OK] Delivered to {to_email}: '{subject}'")
            return True
        except Exception as e:
            logger.error(f"Failed to deliver SMTP email: {e}")
            print(f"❌ [Email ERROR] SMTP delivery failed: {e}")
            return False

    # --------------------------------------------------------------------------
    # A. MORNING INTAKE QUESTIONNAIRE (07:30 AM IST)
    # --------------------------------------------------------------------------
    def send_morning_intake_questionnaire(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches the rich Morning Intake Questionnaire according to Section 2 specification."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"🌅 [Daily Research Brief] Configure Your Paper Harvest Pipeline — {date_str}"
        raw_template = get_morning_questionnaire_template(date_str)

        plain_body = f"""✨ ACADEMIC LITERATURE HARVESTER & VERIFIER
Good morning! ☀️ Ready to run today's literature exploration?
Simply hit 'Reply', fill in your preferences next to the tags below, and hit Send. Everything else is handled automatically! 🚀

--------------------------------------------------------------------------------
📋 SECTION 1: EXECUTION PROFILE & ENVIRONMENT
Configure run metadata and network parameters:
[NAME_OF_RUN]: Run_{date_str}_01
[RUN_TYPE]: Automated ⚙️ (Options: Automated | Manual | Batch)
[LOCATION]: HITS Campus 🏛️ (Options: HITS Campus | Home | Online VPS)
[BATCH_RUN]: No 📦 (Options: Yes | No)
[BATCH_DETAILS]: None 📑 (If Yes: specify batch file name and item position)
[OUTPUT_MODE]: Create New 📄 (Options: Create New | Append to Existing)
[TARGET_SHEET]: None 📊 (If Appending: name of target sheet/file)

🎯 SECTION 2: RESEARCH FOCUS & SUBTOPICS
Define up to 5 core topics with up to 5 subtopics each:
[TOPIC_COUNT]: 2 🔢 (Max: 5)
🔹 Topic 1:
[TOPIC_1]: Fuzzy Machine Learning
[T1_SUBTOPICS]: T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems, Fuzzy Clustering, Membership Tuning
🔹 Topic 2:
[TOPIC_2]: Graph Neural Networks
[T2_SUBTOPICS]: Spectral Clustering, Link Prediction, Graph Attention Networks
(Leave unused topics like [TOPIC_3] blank or delete them)

⚖️ SECTION 3: SCOPE, QUOTAS & TIMEFRAME
[PAPERS_PER_TOPIC]: 250 📚 (Preset choices: 100 | 250 | 500 — Hard cap: 500)
[YEAR_RANGE]: 2021-2026 🗓️ (Format: YYYY-YYYY or 'All Years')
[DOC_TYPE]: Journal Articles Only 📑 (Options: Journal Articles Only | Conference Proceedings | Preprints | All)

🛡️ SECTION 4: VERIFICATION TIERS & PIPELINE MODE
[INST_TOKEN]: True 🔑 (Options: True [Scopus/WoS/IEEE authoritative] | False [Open Access fallback])
[TARGET_INDEX]: Scopus, Web of Science, IEEE Xplore, Crossref 🌐
[QUOTA_STRICTNESS]: Strict 🎯 (Options: Strict [paginate until filled] | Fast-Capped [stop on candidate limit])
--------------------------------------------------------------------------------

💡 Quick Tip: Keep the square brackets `[...]` intact so the intake parser reads your values accurately. Have a productive day of research! ☕🎓
"""

        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Good morning! ☀️ Ready to run today's literature exploration?<br>
            Simply hit <b>Reply</b>, fill in your preferences next to the highlighted tags below, and hit <b>Send</b>. Everything else is handled automatically! 🚀
        </div>

        <!-- Section 1 Card -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px; display: flex; align-items: center;">
                <span>📋 Section 1: Execution Profile & Environment</span>
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; color: #0f172a; line-height: 1.8;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[NAME_OF_RUN]:</span> Run_{date_str}_01<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[RUN_TYPE]:</span> Automated ⚙️ <span style="color: #64748b;">(Options: Automated | Manual | Batch)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[LOCATION]:</span> HITS Campus 🏛️ <span style="color: #64748b;">(Options: HITS Campus | Home | Online VPS)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[BATCH_RUN]:</span> No 📦 <span style="color: #64748b;">(Options: Yes | No)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[BATCH_DETAILS]:</span> None 📑 <span style="color: #64748b;">(If Yes: batch file and item position)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[OUTPUT_MODE]:</span> Create New 📄 <span style="color: #64748b;">(Options: Create New | Append to Existing)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[TARGET_SHEET]:</span> None 📊 <span style="color: #64748b;">(If Appending: name of target sheet/file)</span>
            </div>
        </div>

        <!-- Section 2 Card -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px; display: flex; align-items: center;">
                <span>🎯 Section 2: Research Focus & Subtopics</span>
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; color: #0f172a; line-height: 1.8;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[TOPIC_COUNT]:</span> 2 🔢 <span style="color: #64748b;">(Max: 5)</span><br><br>
                <b>🔹 Topic 1:</b><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[TOPIC_1]:</span> Fuzzy Machine Learning<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[T1_SUBTOPICS]:</span> T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems, Fuzzy Clustering, Membership Tuning<br><br>
                <b>🔹 Topic 2:</b><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[TOPIC_2]:</span> Graph Neural Networks<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[T2_SUBTOPICS]:</span> Spectral Clustering, Link Prediction, Graph Attention Networks<br>
                <span style="color: #94a3b8; font-size: 11px;">(Leave unused topics like [TOPIC_3] blank or delete them)</span>
            </div>
        </div>

        <!-- Section 3 Card -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                <span>⚖️ Section 3: Scope, Quotas & Timeframe</span>
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; color: #0f172a; line-height: 1.8;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[PAPERS_PER_TOPIC]:</span> 250 📚 <span style="color: #64748b;">(Preset: 100 | 250 | 500 — Hard cap: 500)</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[YEAR_RANGE]:</span> 2021-2026 🗓️ <span style="color: #64748b;">(Format: YYYY-YYYY or 'All Years')</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[DOC_TYPE]:</span> Journal Articles Only 📑 <span style="color: #64748b;">(Journal Articles | Conferences | Preprints | All)</span>
            </div>
        </div>

        <!-- Section 4 Card -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                <span>🛡️ Section 4: Verification Tiers & Pipeline Mode</span>
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; color: #0f172a; line-height: 1.8;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[INST_TOKEN]:</span> True 🔑 <span style="color: #64748b;">(True [Scopus/WoS/IEEE authoritative] | False [Open Access])</span><br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[TARGET_INDEX]:</span> Scopus, Web of Science, IEEE Xplore, Crossref 🌐<br>
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[QUOTA_STRICTNESS]:</span> Strict 🎯 <span style="color: #64748b;">(Strict [fill quota] | Fast-Capped [stop on limit])</span>
            </div>
        </div>

        <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; color: #1e40af;">
            💡 <b>Quick Tip:</b> Keep the square brackets <code>[...]</code> intact so the intake parser reads your values accurately. Have a productive day of research! ☕🎓
        </div>
        """

        html_body = _wrap_html_container(
            title="Configure Your Paper Harvest Pipeline",
            header_gradient="linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)",
            header_icon="✨",
            header_subtitle=f"Academic Literature Harvester & Verifier • Daily Research Brief ({date_str})",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    # --------------------------------------------------------------------------
    # B. AFTERNOON CATCH-UP NOTICE (02:00 PM IST)
    # --------------------------------------------------------------------------
    def send_afternoon_reminder(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches the Section 3.A Afternoon Catch-Up Notice."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"☀️ [Afternoon Reminder] Today's Literature Run is Still Pending — {date_str}"

        plain_body = f"""Hey! 👋 Just checking in. Today's paper harvesting run hasn't been triggered yet.

If you'd like to run a literature search today, simply reply to the morning email or use this quick single-line trigger format:

[RUN_TODAY]: Yes | [TOPIC]: Fuzzy Neural Networks | [QUOTA]: 100

If you're busy today, no worries at all — take your time! 🌟
"""

        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Hey! 👋 Just checking in. Today's paper harvesting run hasn't been triggered yet.
        </div>

        <div style="background-color: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <p style="margin: 0 0 10px 0; font-weight: 600; color: #92400e; font-size: 14px;">
                ⚡ Quick Trigger Format:
            </p>
            <p style="margin: 0; font-size: 13px; color: #78350f;">
                Reply directly with this single-line command:
            </p>
            <div style="background: #ffffff; border: 1px solid #fcd34d; border-radius: 6px; padding: 10px 14px; margin-top: 8px; font-family: {CODE_FONT}; font-size: 13px; color: #1e293b;">
                <code>[RUN_TODAY]: Yes | [TOPIC]: Fuzzy Neural Networks | [QUOTA]: 100</code>
            </div>
        </div>

        <div style="font-size: 14px; color: #64748b;">
            If you're busy today, no worries at all — take your time! 🌟
        </div>
        """

        html_body = _wrap_html_container(
            title="Today's Literature Run is Still Pending",
            header_gradient="linear-gradient(135deg, #d97706 0%, #f59e0b 100%)",
            header_icon="☀️",
            header_subtitle=f"Afternoon Check-In (02:00 PM IST) • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    # --------------------------------------------------------------------------
    # C. NIGHT REMINDER NOTICE (09:00 PM IST)
    # --------------------------------------------------------------------------
    def send_night_reminder(self, date_str: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Dispatches the Section 3.B Night Reminder Notice."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"🌙 [Night Check-in] Final Call for Overnight Research Batch — {date_str}"

        plain_body = f"""Good evening! 🌌 The harvester has been idle today.

Would you like to queue up an overnight harvest so your verified papers are ready on your Google Drive by morning? ☕📊

Reply with your topic tags or ignore this email to start fresh tomorrow morning! 🛌💤
"""

        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 20px;">
            Good evening! 🌌 The harvester has been idle today.
        </div>

        <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <div style="font-weight: 600; font-size: 14px; color: #1e293b; margin-bottom: 8px;">
                🌙 Queue Up an Overnight Batch?
            </div>
            <p style="margin: 0; font-size: 14px; color: #475569;">
                Would you like to schedule an overnight harvest so your verified literature database is analyzed, formatted, and synced directly to your Google Drive by tomorrow morning? ☕📊
            </p>
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-top: 12px; font-family: {CODE_FONT}; font-size: 13px; color: #334155;">
                <code>[TOPIC_1]: Fuzzy Machine Learning | [PAPERS_PER_TOPIC]: 250</code>
            </div>
        </div>

        <div style="font-size: 14px; color: #64748b;">
            Reply with your topic tags or ignore this email to start fresh tomorrow morning! 🛌💤
        </div>
        """

        html_body = _wrap_html_container(
            title="Final Call for Overnight Research Batch",
            header_gradient="linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%)",
            header_icon="🌙",
            header_subtitle=f"Night Intake Notice (09:00 PM IST) • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    # --------------------------------------------------------------------------
    # D. PARSE ERROR & CORRECTION EMAIL (Section 4)
    # --------------------------------------------------------------------------
    def send_corrective_email(self, recipient: str, errors: List[str], raw_body: str, date_str: Optional[str] = None) -> bool:
        """Dispatches the Section 4 Parameter Adjustment Needed notice with exact correction guidance."""
        if not date_str:
            date_str = get_ist_now().strftime("%Y-%m-%d")

        subject = f"⚠️ [Harvester Intake Notice] Parameter Adjustment Needed — {date_str}"
        error_bullets = "\n".join(f"• {e}" for e in errors)

        plain_body = f"""🚨 Oops! We noticed a small issue with your configuration reply:

{error_bullets}

🛠️ How to fix:
Reply to this email with corrected lines:
[PAPERS_PER_TOPIC]: 500
[T1_SUBTOPICS]: Subtopic 1, Subtopic 2, Subtopic 3, Subtopic 4, Subtopic 5

The moment your reply arrives, processing begins immediately! ⚡
"""

        error_items_html = "".join(
            f"""<li style="margin-bottom: 8px; color: #991b1b; font-size: 14px;">
                {e}
            </li>""" for e in errors
        )

        content_html = f"""
        <div style="font-size: 15px; color: #334155; margin-bottom: 16px;">
            🚨 Oops! We noticed a small issue with your configuration reply:
        </div>

        <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <ul style="margin: 0; padding-left: 20px;">
                {error_items_html}
            </ul>
        </div>

        <div style="font-weight: 700; font-size: 15px; color: #0f172a; margin-bottom: 8px;">
            🛠️ How to fix:
        </div>
        <p style="font-size: 14px; color: #475569; margin: 0 0 10px 0;">
            Reply to this email with corrected lines:
        </p>

        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; font-family: {CODE_FONT}; font-size: 13px; line-height: 1.8; color: #0f172a; margin-bottom: 16px;">
            <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[PAPERS_PER_TOPIC]:</span> 500<br>
            <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">[T1_SUBTOPICS]:</span> Subtopic 1, Subtopic 2, Subtopic 3, Subtopic 4, Subtopic 5
        </div>

        <div style="font-size: 14px; color: #166534; font-weight: 600;">
            The moment your reply arrives, processing begins immediately! ⚡
        </div>
        """

        html_body = _wrap_html_container(
            title="Parameter Adjustment Needed",
            header_gradient="linear-gradient(135deg, #991b1b 0%, #dc2626 100%)",
            header_icon="⚠️",
            header_subtitle=f"Intake Boundary Validation Notice • {date_str}",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient=recipient)

    # --------------------------------------------------------------------------
    # E. RUN COMPLETION & DISPATCH REPORT (Section 5)
    # --------------------------------------------------------------------------
    def send_run_completion_report(
        self,
        run_config: Dict[str, Any],
        metrics: Dict[str, Any],
        excel_path: str,
        papers: Optional[List[Any]] = None,
        log_text: str = "",
        recipient: Optional[str] = None
    ) -> bool:
        """Dispatches executive completion report with index breakdown and attached .xlsx workbook."""
        run_name = run_config.get("run_name", f"Run_{get_ist_now().strftime('%Y%m%d_%H%M%S')}")
        total_verified = metrics.get("verified_retained", 0)
        subject = f"✅ [Harvest Complete] {run_name} — {total_verified} Papers Verified & Synced! 📚✨"

        timestamp_ist = get_ist_now().strftime("%d %b %Y, %I:%M %p IST")
        location = run_config.get("location", "Home")
        topics = run_config.get("topics", [run_config.get("main_topic", "Literature")])
        topic_count = len(topics)
        raw_harvested = metrics.get("raw_scraped", 0)
        duplicates_dropped = metrics.get("duplicates_removed", 0)

        # Duration formatting
        dur_secs = metrics.get("duration_seconds", 0)
        if dur_secs >= 60:
            duration_formatted = f"{dur_secs // 60}m {dur_secs % 60}s"
        else:
            duration_formatted = f"{dur_secs}s"

        # Index verification breakdown
        if papers:
            scopus_hits = sum(1 for p in papers if getattr(p, "scopus_indexed", False) or "scopus" in str(getattr(p, "verification_source", "")).lower())
            wos_hits = sum(1 for p in papers if getattr(p, "wos_indexed", False) or "wos" in str(getattr(p, "verification_source", "")).lower())
            ieee_hits = sum(1 for p in papers if getattr(p, "ieee_indexed", False) or "ieee" in str(getattr(p, "verification_source", "")).lower())
            oa_hits = sum(1 for p in papers if getattr(p, "open_access", False) or "openalex" in str(getattr(p, "verification_source", "")).lower() or "crossref" in str(getattr(p, "verification_source", "")).lower())
        else:
            scopus_hits = metrics.get("scopus_hits", total_verified if run_config.get("inst_token_flag") else 0)
            wos_hits = metrics.get("wos_hits", 0)
            ieee_hits = metrics.get("ieee_hits", 0)
            oa_hits = metrics.get("open_access_hits", total_verified if not run_config.get("inst_token_flag") else 0)

        filename = os.path.basename(excel_path)
        folder_name = cfg.GDRIVE_FOLDER_ID or "Google Drive / Research Papers"

        plain_body = f"""🎉 RUN SUCCESSFUL: {run_name}
Completed at: {timestamp_ist} | Location: {location} 🏛️

📊 Pipeline Overview:
├─ 🎯 Main Topics Searched: {topic_count} ({', '.join(topics)})
├─ 📥 Total Raw Papers Harvested: {raw_harvested}
├─ 🧹 Duplicates Removed: {duplicates_dropped}
├─ 🏆 Authoritative Verified Count: {total_verified}
└─ ⏱️ Total Execution Duration: {duration_formatted}

🌐 Verification Sources:
├─ 🔬 Elsevier Scopus: {scopus_hits} papers
├─ 🏛️ Clarivate Web of Science: {wos_hits} papers
├─ ⚡ IEEE Xplore: {ieee_hits} papers
└─ 🔓 Crossref / OpenAlex Verified: {oa_hits} papers

☁️ Google Drive Sync: Uploaded to '{folder_name}' folder ✅
📁 Local Archive: Saved in 'output/{filename}' ✅
🧹 Cache Maintenance: Auto-expiring files older than 48 hours cleared.

📎 Attached: '{filename}' (contains full Row 1-10 audit metadata and Row 11+ verified paper dataset).
"""

        content_html = f"""
        <!-- Header Info -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                🎉 RUN SUCCESSFUL: {run_name}
            </div>
            <div style="font-size: 13px; color: #64748b;">
                Completed at: <b>{timestamp_ist}</b> | Location: <b>{location} 🏛️</b>
            </div>
        </div>

        <!-- Pipeline Overview Card -->
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                📊 Pipeline Overview
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; line-height: 1.8; color: #1e293b;">
                ├─ 🎯 Main Topics Searched: <b>{topic_count}</b> <span style="color: #64748b;">({', '.join(topics)})</span><br>
                ├─ 📥 Total Raw Papers Harvested: <b>{raw_harvested}</b><br>
                ├─ 🧹 Duplicates Removed: <b>{duplicates_dropped}</b><br>
                ├─ 🏆 Authoritative Verified Count: <span style="color: #166534; font-weight: 700; background: #dcfce7; padding: 1px 6px; border-radius: 4px;">{total_verified} papers</span><br>
                └─ ⏱️ Total Execution Duration: <b>{duration_formatted}</b>
            </div>
        </div>

        <!-- Verification Sources Card -->
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-weight: 700; font-size: 14px; color: #1e3a8a; margin-bottom: 12px;">
                🌐 Verification Sources
            </div>
            <div style="font-family: {CODE_FONT}; font-size: 13px; line-height: 1.8; color: #1e293b;">
                ├─ 🔬 Elsevier Scopus: <b>{scopus_hits}</b> papers<br>
                ├─ 🏛️ Clarivate Web of Science: <b>{wos_hits}</b> papers<br>
                ├─ ⚡ IEEE Xplore: <b>{ieee_hits}</b> papers<br>
                └─ 🔓 Crossref / OpenAlex Verified: <b>{oa_hits}</b> papers
            </div>
        </div>

        <!-- Cloud & Storage Status Card -->
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="font-weight: 700; font-size: 14px; color: #334155; margin-bottom: 8px;">
                ☁️ Cloud & Storage Status
            </div>
            <div style="font-size: 13px; color: #334155; line-height: 1.7;">
                ☁️ <b>Google Drive Sync:</b> Uploaded to <code>{folder_name}</code> folder ✅<br>
                📁 <b>Local Archive:</b> Saved in <code>output/{filename}</code> ✅<br>
                🧹 <b>Cache Maintenance:</b> Auto-expiring files older than 48 hours cleared.
            </div>
        </div>

        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; font-size: 13px; color: #1e40af;">
            📎 <b>Attached:</b> <code>{filename}</code> (contains full Row 1-10 audit metadata and Row 11+ verified paper dataset).
        </div>
        """

        html_body = _wrap_html_container(
            title=f"Harvest Complete: {run_name}",
            header_gradient="linear-gradient(135deg, #065f46 0%, #059669 50%, #10b981 100%)",
            header_icon="✅",
            header_subtitle=f"{total_verified} Papers Authoritatively Verified & Synchronized 📚✨",
            content_html=content_html
        )
        return self.send(subject, html_body, plain_body, recipient, attachment_paths=[excel_path])

    # Backward-compatible alias
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


# ==============================================================================
# 5. INBOUND IMAP CONFIGURATION LISTENER
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
        Polls unread inbox for emails containing research configuration responses.
        Catches replies to Morning Brief, Reminders, and custom subject tags.
        Returns list of message dicts: {'sender', 'subject', 'body', 'msg_id'}.
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

                        # Filter: Check subject keywords or check if body has configuration tags
                        is_candidate = any(k in subject for k in [
                            "[Daily Research Brief]",
                            "[Harvester Run Config]",
                            "[Afternoon Reminder]",
                            "[Night Check-in]",
                            "[Harvester Intake Notice]",
                            "Re:"
                        ])

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

                        has_config_tags = bool(re.search(r"\[(?:NAME_OF_RUN|TOPIC_1|TOPIC|RUN_TODAY)\]", body, re.IGNORECASE))

                        if not is_candidate and not has_config_tags:
                            continue

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
