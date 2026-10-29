"""
services/drive/quota.py - Google Drive 403 Quota Error Prevention & Pre-Flight Diagnostics.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Root Cause Analysis for HttpError 403:
A Google Cloud Service Account has 0 bytes of personal drive storage quota.
Even if a personal Google Drive folder is shared with the service account email, whenever
the script uploads a file, Google assigns file ownership to the Service Account.
Because the service account has a quota of 0 bytes, Google immediately blocks it with:
    `HttpError 403: Service Accounts do not have storage quota` / `storageQuotaExceeded`.

Two Approved Solutions:
- Method 1 (Quick Fix / Personal @gmail.com): Switch to User OAuth 2.0 (credentials.json + token.json).
  Files are owned by the authenticated personal account, utilizing personal Drive storage.
- Method 2 (Organizational Shared Drive): Keep Service Account, but target a folder inside an
  organizational Google Workspace Shared Drive (Team Drive) with supportsAllDrives=True.
"""

import logging
from typing import Optional

logger = logging.getLogger("DriveQuota")


def format_quota_error_instructions(service_account_email: str) -> str:
    """Formats actionable diagnostic instructions for resolving Drive 403 quota errors."""
    return f"""
❌ [Drive Sync 403 Storage Quota Resolution]
Root Cause: Service accounts have 0 bytes of storage quota. Even if a personal folder is shared,
Google assigns ownership of uploaded files to the service account, causing Google 403 storageQuotaExceeded.

Choose one of two methods to resolve this:
  • Method 1 (Personal @gmail.com - Recommended):
      Switch to User OAuth 2.0. Place your 'credentials.json' (Desktop App OAuth Client ID)
      in the project root. On first run, it generates 'token.json' and uploads files under
      your personal account ownership.
  • Method 2 (Google Workspace Organization / Shared Drive):
      Ensure GDRIVE_FOLDER_ID belongs to a Google Workspace Shared Drive (Team Drive).
      Add '{service_account_email or 'your-service-account@iam.gserviceaccount.com'}' as Content Manager or Contributor.
      Set supportsAllDrives=True in your upload request."""


def validate_upload_quota_preconditions(
    auth_mode: str,
    folder_id: Optional[str],
    service_account_email: str,
    drive_type: Optional[str] = None
) -> bool:
    """
    Executes pre-flight validation of drive type and upload mode before file streaming.
    Returns True if preconditions are met to safely proceed, False otherwise.
    """
    print("\n🔍 [Drive Pre-Flight Check] Validating upload authorization and destination...")

    # Mode 1: User OAuth 2.0
    if auth_mode in ("oauth_user", "oauth_refresh_token"):
        print(f"  🔐 Auth Mode  : USER_OAUTH_2.0 (Personal Drive storage space utilized)")
        print(f"  📂 Destination: {folder_id if folder_id else '[My Drive Root]'}")
        print("  ✅ [Pre-Flight OK] Safe to stream file. Ownership belongs to user account.")
        return True

    # Mode 2: Domain-Wide Delegation
    if auth_mode == "domain_delegation":
        print(f"  🔐 Auth Mode  : DOMAIN_WIDE_DELEGATION (Workspace user pool utilized)")
        print(f"  📂 Destination: {folder_id if folder_id else '[Delegated User Root]'}")
        print("  ✅ [Pre-Flight OK] Safe to stream file. Ownership belongs to delegated user.")
        return True

    # Mode 3: Service Account
    if auth_mode == "service_account":
        print(f"  🔐 Auth Mode  : SERVICE_ACCOUNT ({service_account_email or 'Unknown'})")
        print(f"  📂 Destination: {folder_id if folder_id else '[UNSET - Root Quota Warning]'}")

        if not folder_id:
            msg = format_quota_error_instructions(service_account_email)
            print(msg)
            logger.error(
                f"[DriveQuota] Aborted upload: Service Account '{service_account_email}' has no personal "
                f"Drive quota and GDRIVE_FOLDER_ID is unset."
            )
            return False

        if drive_type == "shared":
            print("  🏢 Drive Type : Google Workspace Shared Drive (Team Drive)")
            print("  ✅ [Pre-Flight OK] Destination belongs to Shared Drive pool (supportsAllDrives=True).")
            return True
        elif drive_type == "personal":
            print("  ⚠️ [Pre-Flight Warning] Destination folder appears to be in a personal My Drive.")
            print("     If upload fails with 403 storageQuotaExceeded, switch to Method 1 (User OAuth).")
            return True
        else:
            print("  📁 Target ID  : Present (streaming with supportsAllDrives=True)")
            return True

    if not auth_mode or auth_mode == "none":
        print("  ❌ [Pre-Flight Error] No valid Google Drive authentication method initialized.")
        return False

    return True
