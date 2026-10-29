"""
services/drive - Google Drive cloud upload and quota management package.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.drive.client import GoogleDriveClient, drive_client
from services.drive.uploader import DriveUploader
from services.drive.mime import get_mime_and_stream
from services.drive.quota import validate_upload_quota_preconditions, format_quota_error_instructions
from services.drive.oauth import load_user_oauth_credentials

__all__ = [
    "GoogleDriveClient",
    "DriveUploader",
    "drive_client",
    "get_mime_and_stream",
    "validate_upload_quota_preconditions",
    "format_quota_error_instructions",
    "load_user_oauth_credentials",
]
