"""
services/drive/auth.py - Google Drive OAuth 2.0 authentication and token management.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.drive.oauth import (
    load_user_oauth_credentials,
    DEFAULT_OAUTH_SCOPES,
    OAUTH_LIBRARIES_AVAILABLE,
)

__all__ = [
    "load_user_oauth_credentials",
    "DEFAULT_OAUTH_SCOPES",
    "OAUTH_LIBRARIES_AVAILABLE",
]
