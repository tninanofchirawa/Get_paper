"""
services/notifications/imap_listener.py - IMAP inbox reader and unread questionnaire reply poller.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict

from config import cfg

logger = logging.getLogger("IMAPListener")


class ImapInboxReader:
    """Connects to IMAP inbox and polls for '[Harvester Run Config]' replies."""

    def __init__(self):
        self.host = cfg.IMAP_HOST
        self.port = cfg.IMAP_PORT
        self.user = cfg.IMAP_USER
        self.password = cfg.IMAP_PASSWORD
        self.use_ssl = cfg.IMAP_USE_SSL

    def _decode_str(self, header_val: str) -> str:
        if not header_val:
            return ""
        decoded_parts = decode_header(header_val)
        result = []
        for part, enc in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)

    def check_incoming_responses(self) -> List[Dict[str, str]]:
        """
        Connects to IMAP server, searches for UNSEEN messages with '[Harvester Run Config]',
        parses their sender and plaintext body, marks them as SEEN, and returns them.
        """
        if not self.user or not self.password:
            return []

        messages: List[Dict[str, str]] = []
        try:
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                mail = imaplib.IMAP4(self.host, self.port)

            mail.login(self.user, self.password)
            mail.select("INBOX")

            status, data = mail.search(None, '(UNSEEN SUBJECT "[Harvester Run Config]")')
            if status != "OK" or not data[0]:
                mail.logout()
                return []

            mail_ids = data[0].split()
            for m_id in mail_ids:
                status, msg_data = mail.fetch(m_id, "(RFC822)")
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_email = response_part[1]
                        msg = email.message_from_bytes(raw_email)

                        subject = self._decode_str(msg.get("Subject", ""))
                        sender = self._decode_str(msg.get("From", ""))

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                cdisp = str(part.get("Content-Disposition"))
                                if ctype == "text/plain" and "attachment" not in cdisp:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset() or "utf-8"
                                        body = payload.decode(charset, errors="replace")
                                        break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                charset = msg.get_content_charset() or "utf-8"
                                body = payload.decode(charset, errors="replace")

                        messages.append({
                            "id": m_id.decode("utf-8"),
                            "sender": sender,
                            "subject": subject,
                            "body": body
                        })

                        # Mark as read/seen
                        mail.store(m_id, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as e:
            logger.error(f"[IMAPListener] Error polling inbox: {e}")

        return messages


# Singleton instance
imap_reader = ImapInboxReader()
