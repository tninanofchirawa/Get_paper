"""
services/notifications/smtp_dispatcher.py - SMTP email transport client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List

from config import cfg

logger = logging.getLogger("SMTPDispatcher")


def send_smtp_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_paths: Optional[List[str]] = None,
    text_content: Optional[str] = None
) -> bool:
    """
    Sends an email via SMTP (e.g. Gmail App Password).
    Returns True on success, False on failure without raising exceptions.
    """
    if not cfg.SMTP_USER or not cfg.SMTP_PASSWORD:
        logger.warning("[SMTPDispatcher] SMTP credentials not configured.")
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{cfg.EMAIL_SENDER_NAME} <{cfg.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        alt_part = MIMEMultipart("alternative")
        if text_content:
            alt_part.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            alt_part.attach(MIMEText(html_content, "html", "utf-8"))
        msg.attach(alt_part)

        if attachment_paths:
            for file_path in attachment_paths:
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    fname = os.path.basename(file_path)
                    part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
                    msg.attach(part)

        server = smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=cfg.DEFAULT_TIMEOUT)
        if cfg.SMTP_USE_TLS:
            server.starttls()
        server.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"[SMTPDispatcher] Delivered email '{subject}' to {to_email}")
        return True

    except Exception as e:
        logger.error(f"[SMTPDispatcher] Delivery failed: {e}")
        print(f"❌ [Email ERROR] SMTP delivery failed: {e}")
        return False
