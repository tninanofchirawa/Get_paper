"""
services/drive/oauth.py - Google Drive User OAuth 2.0 Flow (Method 1).
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Solves 'HttpError 403: Service Accounts do not have storage quota' for personal Google accounts (@gmail.com).
When authenticated as a user via OAuth 2.0, files uploaded are owned by the user's personal Google account,
consuming personal drive quota rather than the service account's zero-byte quota.
"""

import os
import logging
from typing import Optional, List, Any

logger = logging.getLogger("DriveOAuth")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials as UserCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    OAUTH_LIBRARIES_AVAILABLE = True
except ImportError:
    OAUTH_LIBRARIES_AVAILABLE = False


DEFAULT_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]


def load_user_oauth_credentials(
    token_path: str = "token.json",
    credentials_path: str = "credentials.json",
    scopes: Optional[List[str]] = None,
    allow_interactive: bool = False
) -> Optional[Any]:
    """
    Loads or refreshes user OAuth 2.0 credentials from token.json or credentials.json.
    
    1. If token.json exists, loads authorized user tokens.
    2. If expired and refresh_token is present, automatically refreshes the token.
    3. If invalid and allow_interactive=True and credentials.json exists, opens browser login.
    """
    if not OAUTH_LIBRARIES_AVAILABLE:
        logger.debug("[DriveOAuth] google-auth-oauthlib not installed.")
        return None

    scopes = scopes or DEFAULT_OAUTH_SCOPES
    creds = None

    # Step 1: Check for existing token.json
    if os.path.exists(token_path):
        try:
            creds = UserCredentials.from_authorized_user_file(token_path, scopes)
            logger.info(f"[DriveOAuth] Loaded existing credentials from '{token_path}'.")
        except Exception as e:
            logger.warning(f"[DriveOAuth] Could not parse '{token_path}': {e}")
            creds = None

    # Step 2: Refresh token if expired
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                logger.info("[DriveOAuth] Refreshing expired access token via refresh_token...")
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                logger.info(f"[DriveOAuth] Successfully refreshed and persisted tokens to '{token_path}'.")
            except Exception as e:
                logger.warning(f"[DriveOAuth] Token refresh failed: {e}")
                creds = None
        else:
            creds = None

    # Step 3: Interactive flow if explicitly permitted and credentials.json exists
    if not creds and allow_interactive and os.path.exists(credentials_path):
        try:
            print("\n🌐 [Google Drive OAuth] Initiating User Authentication Flow...")
            print("  Opening browser window to authenticate your personal Google account...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"  ✅ [Google Drive OAuth] Authentication successful! Saved to '{token_path}'.\n")
        except Exception as e:
            logger.error(f"[DriveOAuth] InstalledAppFlow failed: {e}")
            creds = None

    return creds
