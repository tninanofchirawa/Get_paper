"""
drive_sync.py - Google Drive cloud upload and synchronization (Backward Compatibility Wrapper).
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to services.drive.
"""

try:
    from googleapiclient.http import MediaFileUpload
except ImportError:
    MediaFileUpload = None

from services.drive import (
    GoogleDriveClient,
    drive_client,
    get_mime_and_stream,
    validate_upload_quota_preconditions,
    format_quota_error_instructions,
)
from services.drive.oauth import load_user_oauth_credentials

__all__ = [
    "GoogleDriveClient",
    "drive_client",
    "get_mime_and_stream",
    "validate_upload_quota_preconditions",
    "format_quota_error_instructions",
    "MediaFileUpload",
]

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 GOOGLE DRIVE USER OAUTH 2.0 AUTHENTICATION SETUP")
    print("=" * 60)
    creds = load_user_oauth_credentials(allow_interactive=True)
    if creds and creds.valid:
        print("🎉 [Success] Authentication complete! 'token.json' has been created and verified.")
        print("   Future pipeline runs will automatically upload files using your personal Drive storage quota.")
    else:
        print("❌ [Notice] Authentication flow was not completed.")
