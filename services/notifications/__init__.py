"""
services/notifications - Email dispatch, IMAP listening, and template package.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.notifications.tag_parser import parse_run_config_tags, clean_field_value, get_ist_now
from services.notifications.smtp_dispatcher import send_smtp_email
from services.notifications.mailgun_dispatcher import send_mailgun_email
from services.notifications.sendgrid_dispatcher import send_sendgrid_email
from services.notifications.imap_listener import ImapInboxReader, imap_reader
from services.notifications.dispatcher import EmailDispatcher, email_dispatcher
from services.notifications.templates import wrap_html_container, get_morning_questionnaire_template

__all__ = [
    "parse_run_config_tags",
    "clean_field_value",
    "get_ist_now",
    "send_smtp_email",
    "send_mailgun_email",
    "send_sendgrid_email",
    "ImapInboxReader",
    "imap_reader",
    "EmailDispatcher",
    "email_dispatcher",
    "wrap_html_container",
    "get_morning_questionnaire_template",
]
