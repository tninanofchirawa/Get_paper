"""
services/notifications/mailgun_dispatcher.py - Mailgun REST API transport client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import logging
from typing import Optional, List
import requests

from config import cfg

logger = logging.getLogger("MailgunDispatcher")


def send_mailgun_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_paths: Optional[List[str]] = None,
    text_content: Optional[str] = None
) -> bool:
    """Sends an email via Mailgun Messages API."""
    if not cfg.MAILGUN_API_KEY or not cfg.MAILGUN_DOMAIN:
        logger.warning("[MailgunDispatcher] MAILGUN_API_KEY or MAILGUN_DOMAIN not configured.")
        return False

    url = f"https://api.mailgun.net/v3/{cfg.MAILGUN_DOMAIN}/messages"
    auth = ("api", cfg.MAILGUN_API_KEY)
    data = {
        "from": f"{cfg.EMAIL_SENDER_NAME} <mailgun@{cfg.MAILGUN_DOMAIN}>",
        "to": [to_email],
        "subject": subject,
        "text": text_content or "",
        "html": html_content
    }

    files = []
    if attachment_paths:
        for ap in attachment_paths:
            if ap and os.path.exists(ap):
                files.append(("attachment", (os.path.basename(ap), open(ap, "rb"))))

    try:
        resp = requests.post(url, auth=auth, data=data, files=files if files else None, timeout=cfg.DEFAULT_TIMEOUT)
        for _, f_tuple in files:
            f_tuple[1].close()

        if resp.status_code in (200, 201):
            logger.info(f"[MailgunDispatcher] Delivered email '{subject}' to {to_email}")
            return True
        else:
            logger.error(f"[MailgunDispatcher] Failed ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[MailgunDispatcher] Exception: {e}")
        return False
