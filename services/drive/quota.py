"""
services/drive/quota.py - Google Drive 403 quota error prevention and diagnostics.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging

logger = logging.getLogger("DriveQuota")


def format_quota_error_instructions(service_account_email: str) -> str:
    """Formats actionable diagnostic instructions for resolving Drive 403 quota errors."""
    return f"""
❌ [Drive Sync 403 Quota Error Prevention]
Google Service Accounts have NO personal Google Drive storage quota.
To resolve this, set GDRIVE_FOLDER_ID in your .env to:
  • Option A (Recommended): A Google Shared Drive (Team Drive) where the service account ({service_account_email or 'service account'}) is added as Content Manager or Contributor.
  • Option B: A folder on your personal Google Drive that you have shared with '{service_account_email or 'your service account email'}' with Editor permissions.
Upload aborted safely to prevent Google 403 rejection."""


def validate_upload_quota_preconditions(auth_mode: str, folder_id: str, service_account_email: str) -> bool:
    """
    Validates whether preconditions to avoid HTTP 403 quota error are met.
    Returns True if safe to proceed, False otherwise.
    """
    if auth_mode == "service_account" and not folder_id:
        msg = format_quota_error_instructions(service_account_email)
        print(msg)
        logger.error(f"[DriveQuota] Aborted upload: Service Account '{service_account_email}' has no personal Drive quota and GDRIVE_FOLDER_ID is unset.")
        return False
    return True
