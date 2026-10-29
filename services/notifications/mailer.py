"""
services/notifications/mailer.py - Mailer and alert dispatcher interface.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.notifications.dispatcher import EmailDispatcher, email_dispatcher
from services.notifications.smtp_dispatcher import send_smtp_email
from services.notifications.mailgun_dispatcher import send_mailgun_email
from services.notifications.sendgrid_dispatcher import send_sendgrid_email

Mailer = EmailDispatcher
mailer = email_dispatcher

__all__ = [
    "EmailDispatcher",
    "email_dispatcher",
    "Mailer",
    "mailer",
    "send_smtp_email",
    "send_mailgun_email",
    "send_sendgrid_email",
]
