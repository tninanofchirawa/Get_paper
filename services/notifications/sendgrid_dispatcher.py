"""
services/notifications/sendgrid_dispatcher.py - SendGrid v3 Web API transport client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import base64
import logging
from typing import Optional, List
import requests

from config import cfg

logger = logging.getLogger("SendGridDispatcher")


def send_sendgrid_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_paths: Optional[List[str]] = None,
    text_content: Optional[str] = None
) -> bool:
    """Sends an email via SendGrid v3 mail/send endpoint."""
    if not cfg.SENDGRID_API_KEY:
        logger.warning("[SendGridDispatcher] SENDGRID_API_KEY not configured.")
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {cfg.SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    sender_email = cfg.SMTP_USER or cfg.POLITE_EMAIL
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender_email, "name": cfg.EMAIL_SENDER_NAME},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_content or "Please open this email in an HTML compatible client."},
            {"type": "text/html", "value": html_content}
        ]
    }

    if attachment_paths:
        attachments = []
        for ap in attachment_paths:
            if ap and os.path.exists(ap):
                try:
                    with open(ap, "rb") as f:
                        b64_content = base64.b64encode(f.read()).decode("utf-8")
                    attachments.append({
                        "content": b64_content,
                        "filename": os.path.basename(ap),
                        "type": "text/csv" if ap.endswith(".csv") else "application/octet-stream",
                        "disposition": "attachment"
                    })
                except Exception as e:
                    logger.warning(f"[SendGridDispatcher] Could not encode '{ap}': {e}")
        if attachments:
            payload["attachments"] = attachments

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=cfg.DEFAULT_TIMEOUT)
        if resp.status_code in (200, 202):
            logger.info(f"[SendGridDispatcher] Delivered email '{subject}' to {to_email}")
            return True
        else:
            logger.error(f"[SendGridDispatcher] Failed ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[SendGridDispatcher] Exception: {e}")
        return False
