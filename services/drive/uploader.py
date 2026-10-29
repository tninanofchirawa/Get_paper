"""
services/drive/uploader.py - Google Drive file upload handlers and synchronization client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.drive.client import (
    GoogleDriveClient,
    drive_client,
    GOOGLE_DRIVE_INSTALLED,
)
from services.drive.mime import get_mime_and_stream
from services.drive.quota import (
    validate_upload_quota_preconditions,
    format_quota_error_instructions,
)

DriveUploader = GoogleDriveClient

__all__ = [
    "GoogleDriveClient",
    "DriveUploader",
    "drive_client",
    "get_mime_and_stream",
    "validate_upload_quota_preconditions",
    "format_quota_error_instructions",
    "GOOGLE_DRIVE_INSTALLED",
]
