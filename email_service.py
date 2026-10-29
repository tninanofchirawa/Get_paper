"""
email_service.py - Notification and IMAP service (Backward Compatibility Wrapper).
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to services.notifications.
"""

from services.notifications import (
    EmailDispatcher,
    email_dispatcher,
    ImapInboxReader,
    imap_reader,
    parse_run_config_tags,
    clean_field_value,
    get_ist_now,
    send_smtp_email,
    send_mailgun_email,
    send_sendgrid_email,
    wrap_html_container,
    get_morning_questionnaire_template,
)

# Backward-compatible alias
IMAPQuestionnaireReader = ImapInboxReader

__all__ = [
    "EmailDispatcher",
    "email_dispatcher",
    "ImapInboxReader",
    "IMAPQuestionnaireReader",
    "imap_reader",
    "parse_run_config_tags",
    "clean_field_value",
    "get_ist_now",
    "send_smtp_email",
    "send_mailgun_email",
    "send_sendgrid_email",
    "wrap_html_container",
    "get_morning_questionnaire_template",
]
