"""
services/drive/client.py - Google Drive API v3 Client with Multi-Auth & Quota Management.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Implements:
- Method 1: User OAuth 2.0 (credentials.json + token.json) for personal Google accounts (@gmail.com).
  Files uploaded consume personal drive quota, completely avoiding service account 403 errors.
- Method 2: Google Workspace Shared Drive (Team Drive) with supportsAllDrives=True.
- Pre-flight validation logging checking upload mode and drive type before file streaming.
- Resumable chunked uploads with payload size logging (5 KB - 400 KB).
- Optional gzip compression via services.drive.mime.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config import cfg
from services.drive.mime import get_mime_and_stream
from services.drive.quota import validate_upload_quota_preconditions, format_quota_error_instructions
from services.drive.oauth import load_user_oauth_credentials

logger = logging.getLogger("DriveClient")

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials as OAuthCredentials
    GOOGLE_DRIVE_INSTALLED = True
except ImportError:
    GOOGLE_DRIVE_INSTALLED = False


class GoogleDriveClient:
    """Manages automated uploads to Google Drive using Drive API v3 with quota error prevention."""

    def __init__(
        self,
        folder_id: Optional[str] = None,
        service_account_path: Optional[str] = None
    ):
        self.folder_id = folder_id if folder_id is not None else cfg.GDRIVE_FOLDER_ID
        self.shared_drive_id = cfg.GDRIVE_SHARED_DRIVE_ID
        self.service_account_path = service_account_path or cfg.GDRIVE_SERVICE_ACCOUNT_JSON
        self.service = None
        self.auth_mode: str = "none"
        self.service_account_email: str = ""
        self.last_upload_info: Dict[str, Any] = {}
        self._init_service()

    def _init_service(self):
        """Initializes Drive API v3 service across Method 1 (User OAuth) or Method 2 (Service Account)."""
        if not GOOGLE_DRIVE_INSTALLED:
            logger.warning("[DriveClient] Google API client libraries not installed.")
            return

        scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]

        # Determine if interactive browser login should be allowed on first run
        is_test_env = "unittest" in sys.modules or "pytest" in sys.modules
        base_dir = cfg.BASE_DIR
        has_credentials = (
            (base_dir / "credentials.json").exists()
            or (base_dir / "Credential.json").exists()
            or os.path.exists("credentials.json")
            or os.path.exists("Credential.json")
        )
        has_token = (
            (base_dir / "token.json").exists()
            or (base_dir / "Token.json").exists()
            or os.path.exists("token.json")
            or os.path.exists("Token.json")
        )
        allow_interactive = (not is_test_env) and has_credentials and (not has_token)

        # Method 1: User-level OAuth 2.0 (token.json or credentials.json)
        oauth_creds = load_user_oauth_credentials(
            token_path=str(base_dir / "token.json"),
            credentials_path=str(base_dir / "credentials.json"),
            scopes=scopes,
            allow_interactive=allow_interactive
        )
        if oauth_creds:
            try:
                self.service = build("drive", "v3", credentials=oauth_creds)
                self.auth_mode = "oauth_user"
                logger.info("[DriveClient] Initialized via Method 1 (User OAuth 2.0).")
                print("☁️ [Drive Sync] Authenticated via Method 1 (User OAuth 2.0 - Personal Account).")
                return
            except Exception as e:
                logger.warning(f"[DriveClient] Method 1 User OAuth init failed: {e}")

        # Method 1B: User-level OAuth 2.0 from environment variables
        if cfg.GDRIVE_REFRESH_TOKEN and cfg.GDRIVE_CLIENT_ID and cfg.GDRIVE_CLIENT_SECRET:
            try:
                creds = OAuthCredentials(
                    None,
                    refresh_token=cfg.GDRIVE_REFRESH_TOKEN,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=cfg.GDRIVE_CLIENT_ID,
                    client_secret=cfg.GDRIVE_CLIENT_SECRET,
                    scopes=scopes
                )
                self.service = build("drive", "v3", credentials=creds)
                self.auth_mode = "oauth_user"
                logger.info("[DriveClient] Initialized via Method 1B (OAuth Refresh Token Env).")
                print("☁️ [Drive Sync] Authenticated via Method 1B (User OAuth Refresh Token).")
                return
            except Exception as e:
                logger.warning(f"[DriveClient] Method 1B User OAuth init failed: {e}")

        # Method 2: Service Account credentials (Workspace Shared Drive)
        sa_info = None
        resolved_sa_path = self.service_account_path
        if not os.path.exists(resolved_sa_path):
            candidate_sa = base_dir / self.service_account_path
            if candidate_sa.exists():
                resolved_sa_path = str(candidate_sa)

        if cfg.GDRIVE_SERVICE_ACCOUNT_RAW:
            try:
                sa_info = json.loads(cfg.GDRIVE_SERVICE_ACCOUNT_RAW)
            except Exception:
                pass
        elif os.path.exists(resolved_sa_path):
            try:
                with open(resolved_sa_path, "r", encoding="utf-8") as f:
                    sa_info = json.load(f)
            except Exception:
                pass

        if sa_info:
            self.service_account_email = sa_info.get("client_email", "")
            try:
                if cfg.GDRIVE_DELEGATED_USER:
                    creds = service_account.Credentials.from_service_account_info(
                        sa_info,
                        scopes=scopes,
                        subject=cfg.GDRIVE_DELEGATED_USER
                    )
                    self.auth_mode = "domain_delegation"
                    logger.info(f"[DriveClient] Domain-wide delegation for user: {cfg.GDRIVE_DELEGATED_USER}")
                else:
                    creds = service_account.Credentials.from_service_account_info(
                        sa_info,
                        scopes=scopes
                    )
                    self.auth_mode = "service_account"

                self.service = build("drive", "v3", credentials=creds)
                logger.info(f"[DriveClient] Service account authenticated: {self.service_account_email}")
                print(f"☁️ [Drive Sync] Service Account loaded: {self.service_account_email}")

                if not self.folder_id and not self.shared_drive_id:
                    print("⚠️ [Drive Sync Notice] GDRIVE_FOLDER_ID not set. Service accounts do NOT have personal root storage quota.")
            except Exception as e:
                logger.warning(f"[DriveClient] Service account initialization error: {e}")

    def detect_drive_type(self, folder_id: Optional[str]) -> Optional[str]:
        """Queries drive metadata to detect whether folder is in a Shared Drive or personal My Drive."""
        if not self.service or not folder_id:
            return None
        try:
            res = self.service.files().get(
                fileId=folder_id,
                supportsAllDrives=True,
                fields="id, name, driveId"
            ).execute()
            return "shared" if res.get("driveId") else "personal"
        except Exception:
            return None

    def upload_file(
        self,
        file_path: str,
        target_folder_id: Optional[str] = None,
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """Uploads file to Google Drive with pre-flight validation and supportsAllDrives=True."""
        if not os.path.exists(file_path):
            logger.error(f"[DriveClient] Local file not found: {file_path}")
            return None

        folder = target_folder_id or self.folder_id or self.shared_drive_id

        # Pre-flight drive type and upload mode validation
        drive_type = self.detect_drive_type(folder) if self.service else None
        if not validate_upload_quota_preconditions(self.auth_mode, folder, self.service_account_email, drive_type):
            return None

        if not self.service:
            logger.warning("[DriveClient] Google Drive service not initialized.")
            return None

        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024.0
        upload_title = custom_filename or os.path.basename(file_path)

        mime_type, actual_path, is_compressed = get_mime_and_stream(file_path, enable_gzip=cfg.GDRIVE_ENABLE_GZIP)

        file_metadata: Dict[str, Any] = {
            "name": upload_title,
        }
        if folder:
            file_metadata["parents"] = [folder]

        print(f"\n☁️ [Drive Sync] Preparing upload for: '{upload_title}'")
        print(f"  📦 Payload Size   : {file_size_bytes} bytes ({file_size_kb:.2f} KB)")
        print(f"  🔐 Auth Mode      : {self.auth_mode.upper()}")
        print(f"  📂 Target Folder  : {folder if folder else '[Root - Quota Warning]'}")

        try:
            media = MediaFileUpload(
                actual_path,
                mimetype=mime_type,
                resumable=True
            )

            print("  🚀 Uploading stream via Drive API v3 (supportsAllDrives=True)...")
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink, size",
                supportsAllDrives=True
            ).execute()

            file_id = uploaded_file.get("id")
            web_link = uploaded_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"

            self.last_upload_info = {
                "file_id": file_id,
                "title": upload_title,
                "link": web_link,
                "size_bytes": file_size_bytes,
                "folder_id": folder
            }

            print(f"  ✅ [Drive Sync OK] Upload Successful!")
            print(f"  📄 File Title : {upload_title}")
            print(f"  🆔 File ID    : {file_id}")
            print(f"  🔗 Link       : {web_link}")

            # Clean temporary gzip file if created
            if is_compressed and actual_path != file_path and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except Exception:
                    pass

            return file_id

        except Exception as e:
            err_msg = str(e)
            if "storage quota" in err_msg.lower() or "403" in err_msg or "storagequotaexceeded" in err_msg.lower():
                print(f"❌ [Drive Sync Quota Error] Google 403: {err_msg}")
                print(format_quota_error_instructions(self.service_account_email))
            else:
                print(f"❌ [Drive Sync Error] Upload failed: {err_msg}")
            logger.error(f"[DriveClient] Upload failed: {e}")
            return None

    def get_last_link(self) -> Optional[str]:
        return self.last_upload_info.get("link")


# Global singleton instance
drive_client = GoogleDriveClient()
