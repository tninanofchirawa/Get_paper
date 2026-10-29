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

__all__ = [
    "GoogleDriveClient",
    "drive_client",
    "get_mime_and_stream",
    "validate_upload_quota_preconditions",
    "format_quota_error_instructions",
    "MediaFileUpload",
]
