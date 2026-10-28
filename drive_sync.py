"""
drive_sync.py - Google Drive API v3 upload and cloud synchronization client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config import cfg

logger = logging.getLogger("GoogleDriveSync")

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    GOOGLE_DRIVE_INSTALLED = True
except ImportError:
    GOOGLE_DRIVE_INSTALLED = False

try:
    import requests
except ImportError:
    requests = None
    import urllib.request


class GoogleDriveClient:
    """
    Manages automated uploads to Google Drive using Drive API v3 Service Account credentials.
    Supports zero-install public download syncing for lab machines.
    """

    def __init__(
        self,
        folder_id: Optional[str] = None,
        service_account_path: Optional[str] = None
    ):
        self.folder_id = folder_id or cfg.GDRIVE_FOLDER_ID
        self.service_account_path = service_account_path or cfg.GDRIVE_SERVICE_ACCOUNT_JSON
        self.service = None
        self._init_service()

    def _init_service(self):
        """Initializes the Google Drive v3 client service if credentials exist."""
        if not GOOGLE_DRIVE_INSTALLED:
            logger.info("google-api-python-client is not installed. Drive uploads will run in dry-run mode.")
            return

        scopes = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

        # Option A: Service account JSON string in environment variable
        if cfg.GDRIVE_SERVICE_ACCOUNT_RAW:
            try:
                info = json.loads(cfg.GDRIVE_SERVICE_ACCOUNT_RAW)
                creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
                self.service = build("drive", "v3", credentials=creds)
                logger.info("Google Drive API v3 service successfully initialized via RAW credentials.")
                return
            except Exception as e:
                logger.warning(f"Could not initialize Drive credentials from GDRIVE_SERVICE_ACCOUNT_RAW: {e}")

        # Option B: Service account JSON file on disk
        if self.service_account_path and os.path.exists(self.service_account_path):
            try:
                creds = service_account.Credentials.from_service_account_file(self.service_account_path, scopes=scopes)
                self.service = build("drive", "v3", credentials=creds)
                logger.info(f"Google Drive API v3 service successfully initialized via '{self.service_account_path}'.")
                return
            except Exception as e:
                logger.warning(f"Could not initialize Drive credentials from '{self.service_account_path}': {e}")

        logger.debug("No valid Google Drive Service Account credentials found. Drive uploads will be skipped.")

    def upload_file(self, local_path: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """
        Uploads an Excel or CSV file to the designated Google Drive folder.
        Returns the Drive file ID if successful, or None.
        """
        if not os.path.exists(local_path):
            logger.error(f"[Drive Upload] Local file does not exist: {local_path}")
            return None

        filename = custom_filename or os.path.basename(local_path)
        print(f"[Drive Sync] Uploading '{filename}' to Google Drive...")

        if not self.service:
            print(f"[Drive Sync] Service account credentials not configured. File saved locally at: {local_path}")
            return None

        try:
            file_metadata = {"name": filename}
            if self.folder_id:
                file_metadata["parents"] = [self.folder_id]

            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if filename.lower().endswith(".csv"):
                mime_type = "text/csv"

            media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink"
            ).execute()

            file_id = uploaded_file.get("id")
            link = uploaded_file.get("webViewLink", "")
            print(f"✅ [Drive Sync] File successfully uploaded! File ID: {file_id} | Link: {link}")
            logger.info(f"Uploaded '{filename}' to Google Drive (ID: {file_id})")
            return file_id

        except Exception as e:
            logger.error(f"[Drive Sync] Upload failed: {e}")
            print(f"❌ [Drive Sync] Upload error: {e}")
            return None

    def download_public_file(self, file_id: str, output_filename: str) -> bool:
        """Downloads a publicly shared Google Drive file without requiring API keys."""
        dest_path = os.path.join(cfg.INPUT_DIR, output_filename)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        print(f"Downloading from Google Drive (ID: {file_id}) -> {dest_path}...")

        try:
            if requests is not None:
                resp = requests.get(download_url, timeout=30, stream=True)
                if resp.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"✅ Successfully downloaded {output_filename} ({os.path.getsize(dest_path)} bytes).")
                    return True
                else:
                    logger.error(f"Download HTTP {resp.status_code}")
                    return False
            else:
                urllib.request.urlretrieve(download_url, dest_path)
                return True
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return False

    def sync_from_env(self) -> int:
        """Downloads files specified in GDRIVE_FILE_ID or GDRIVE_DOWNLOAD_LIST."""
        single_id = os.environ.get("GDRIVE_FILE_ID", "").strip()
        single_name = os.environ.get("GDRIVE_FILE_NAME", "downloaded_candidate.csv").strip()
        downloaded = 0

        if single_id:
            if self.download_public_file(single_id, single_name):
                downloaded += 1

        json_list = os.environ.get("GDRIVE_DOWNLOAD_LIST", "").strip()
        if json_list:
            try:
                mapping = json.loads(json_list)
                for fid, fname in mapping.items():
                    if self.download_public_file(fid, fname):
                        downloaded += 1
            except Exception as e:
                logger.warning(f"Could not parse GDRIVE_DOWNLOAD_LIST: {e}")

        return downloaded


# Global client instance
drive_client = GoogleDriveClient()
