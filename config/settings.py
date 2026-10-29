"""
config/settings.py - Centralized configuration settings dataclass and singleton instance.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from config.env import load_env_file
from config.constants import (
    DEFAULT_QUOTA,
    HARD_CAP_TOPICS,
    HARD_CAP_SUBTOPICS_PER_TOPIC,
    HARD_CAP_QUOTA_PER_TOPIC,
    OPENALEX_RATE_LIMIT,
    CROSSREF_RATE_LIMIT,
    ARXIV_RATE_DELAY,
    SEMANTIC_SCHOLAR_RATE_LIMIT,
    SCOPUS_SNAIL_PACE_SECONDS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    BACKOFF_FACTOR,
)

# Ensure environment variables are loaded
load_env_file()


@dataclass
class PipelineConfig:
    # 1. Identity & Polite Pool
    POLITE_EMAIL: str = os.getenv("POLITE_EMAIL", os.getenv("RESEARCHER_EMAIL", "researcher@university.edu")).strip()
    RESEARCHER_EMAIL: str = os.getenv("RESEARCHER_EMAIL", POLITE_EMAIL).strip()
    APP_NAME: str = "Unified Academic Paper Harvester & Verifier"
    APP_VERSION: str = "4.0.0"
    USER_AGENT: str = f"AcademicHarvesterVerifier/4.0 (mailto:{POLITE_EMAIL})"

    # 2. Institutional Verification API Credentials (Branch 1)
    ELSEVIER_API_KEY: str = os.getenv("ELSEVIER_API_KEY", "").strip()
    ELSEVIER_INST_TOKEN: str = os.getenv("ELSEVIER_INST_TOKEN", "").strip()
    WOS_API_KEY: str = os.getenv("WOS_API_KEY", "").strip()
    IEEE_API_KEY: str = os.getenv("IEEE_API_KEY", "").strip()

    # Academic Harvesting API Keys
    OPENALEX_API_KEY: str = os.getenv("OPENALEX_API_KEY", "").strip()
    # Semantic Scholar key strictly in .env under S2_API_KEY (with backward compatible fallback)
    S2_API_KEY: str = os.getenv("S2_API_KEY", os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")).strip()
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", S2_API_KEY).strip()

    # Optional Multi-Provider Email Delivery Keys
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY", "").strip()
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN", "").strip()
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "").strip()

    # Local Master Journal Databases (Branch 2 Fallback)
    SCOPUS_LOCAL_DB_PATH: str = os.getenv("SCOPUS_LOCAL_DB_PATH", "data/scopus_source_list.xlsx")
    WOS_LOCAL_DB_PATH: str = os.getenv("WOS_LOCAL_DB_PATH", "data/wos_master_journal_list.csv")

    # 3. Rate Limits & Pacing Controls
    OPENALEX_RATE_LIMIT: float = OPENALEX_RATE_LIMIT
    CROSSREF_RATE_LIMIT: float = CROSSREF_RATE_LIMIT
    ARXIV_RATE_DELAY: float = ARXIV_RATE_DELAY
    SEMANTIC_SCHOLAR_RATE_LIMIT: float = SEMANTIC_SCHOLAR_RATE_LIMIT  # 1.0 req/sec strict
    SCOPUS_SNAIL_PACE_SECONDS: float = SCOPUS_SNAIL_PACE_SECONDS
    DEFAULT_TIMEOUT: int = int(os.getenv("PAPER_HARVESTER_TIMEOUT", str(DEFAULT_TIMEOUT)))
    MAX_RETRIES: int = MAX_RETRIES
    BACKOFF_FACTOR: float = BACKOFF_FACTOR

    # 4. Quotas & Operational Limits
    DEFAULT_QUOTA: int = DEFAULT_QUOTA
    HARD_CAP_TOPICS: int = HARD_CAP_TOPICS
    HARD_CAP_SUBTOPICS_PER_TOPIC: int = HARD_CAP_SUBTOPICS_PER_TOPIC
    HARD_CAP_QUOTA_PER_TOPIC: int = HARD_CAP_QUOTA_PER_TOPIC

    # 5. 100% Free Gmail SMTP & IMAP Settings
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "smtp").lower()
    RECIPIENT_EMAIL: str = os.getenv("RECIPIENT_EMAIL", POLITE_EMAIL).strip()
    EMAIL_SENDER_NAME: str = os.getenv("EMAIL_SENDER_NAME", "Paper Pipeline Automation").strip()
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USER: str = os.getenv("IMAP_USER", SMTP_USER).strip()
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", SMTP_PASSWORD).strip()
    IMAP_USE_SSL: bool = os.getenv("IMAP_USE_SSL", "true").lower() in ("true", "1", "yes")
    IMAP_POLL_INTERVAL_SECONDS: int = int(os.getenv("IMAP_POLL_INTERVAL_SECONDS", "120"))

    # 6. Google Drive v3 Settings
    GDRIVE_FOLDER_ID: str = os.getenv("GDRIVE_FOLDER_ID", "").strip()
    GDRIVE_SHARED_DRIVE_ID: str = os.getenv("GDRIVE_SHARED_DRIVE_ID", "").strip()
    GDRIVE_SERVICE_ACCOUNT_JSON: str = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "service_account.json").strip()
    GDRIVE_SERVICE_ACCOUNT_RAW: str = os.getenv("GDRIVE_SERVICE_ACCOUNT_RAW", "").strip()
    GDRIVE_DELEGATED_USER: str = os.getenv("GDRIVE_DELEGATED_USER", "").strip()
    GDRIVE_REFRESH_TOKEN: str = os.getenv("GDRIVE_REFRESH_TOKEN", "").strip()
    GDRIVE_CLIENT_ID: str = os.getenv("GDRIVE_CLIENT_ID", "").strip()
    GDRIVE_CLIENT_SECRET: str = os.getenv("GDRIVE_CLIENT_SECRET", "").strip()
    GDRIVE_ENABLE_GZIP: bool = os.getenv("GDRIVE_ENABLE_GZIP", "false").lower() in ("true", "1", "yes")

    # 7. Paths & Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "pipeline.db"))
    INPUT_DIR: str = os.getenv("INPUT_DIR", str(BASE_DIR / "input"))
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))
    CACHE_DIR: str = os.getenv("CACHE_DIR", str(BASE_DIR / "cache"))
    LOGS_DIR: str = os.getenv("LOGS_DIR", str(BASE_DIR / "logs"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))
    CONFIG_DIR: str = os.getenv("CONFIG_DIR", str(BASE_DIR / "config"))
    APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

    @property
    def has_scopus_credentials(self) -> bool:
        """Returns True if BOTH API key and Institutional Token are supplied."""
        return bool(self.ELSEVIER_API_KEY and self.ELSEVIER_INST_TOKEN)

    @property
    def has_institutional_credentials(self) -> bool:
        """Returns True if any institutional token/key is available."""
        return bool(self.has_scopus_credentials or self.WOS_API_KEY or self.IEEE_API_KEY)

    def get_key_pool(self, service: str) -> List[str]:
        """Returns a list of available API keys for a service to enable key rotation / pooling."""
        env_val = os.getenv(f"{service.upper()}_API_KEYS", "").strip()
        if env_val:
            keys = [k.strip() for k in env_val.split(",") if k.strip()]
            if keys:
                return keys
        if service.lower() in ("semantic_scholar", "s2"):
            primary = self.S2_API_KEY or self.SEMANTIC_SCHOLAR_API_KEY
            return [primary] if primary else []
        single_key = getattr(self, f"{service.upper()}_API_KEY", "")
        return [single_key] if single_key else []

    def get_http_headers(self, service: str = "generic") -> Dict[str, str]:
        """Generates standard polite pool and API-specific headers."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        if service == "crossref" and self.POLITE_EMAIL:
            headers["User-Agent"] = f"AcademicHarvester/4.0 (mailto:{self.POLITE_EMAIL})"
        elif service == "openalex":
            if self.POLITE_EMAIL:
                headers["User-Agent"] = f"AcademicHarvester/4.0 (mailto:{self.POLITE_EMAIL})"
            if self.OPENALEX_API_KEY:
                headers["api_key"] = self.OPENALEX_API_KEY
        elif service == "scopus":
            if self.ELSEVIER_API_KEY:
                headers["X-ELS-APIKey"] = self.ELSEVIER_API_KEY
            if self.ELSEVIER_INST_TOKEN:
                headers["X-ELS-Insttoken"] = self.ELSEVIER_INST_TOKEN
        elif service == "wos":
            if self.WOS_API_KEY:
                headers["X-ApiKey"] = self.WOS_API_KEY
        elif service == "ieee":
            if self.IEEE_API_KEY:
                headers["apikey"] = self.IEEE_API_KEY
        elif service in ("semantic_scholar", "s2", "semanticscholar"):
            # Ensure headers include 'x-api-key': os.getenv('S2_API_KEY') on every outbound request
            s2_key = os.getenv("S2_API_KEY", self.S2_API_KEY)
            if s2_key:
                headers["x-api-key"] = s2_key
        return headers

    def ensure_directories(self):
        """Ensures that all application directories exist."""
        for p in [self.INPUT_DIR, self.OUTPUT_DIR, self.CACHE_DIR, self.LOGS_DIR, self.TEMP_DIR, self.CONFIG_DIR, os.path.dirname(self.DATABASE_PATH)]:
            if p:
                os.makedirs(p, exist_ok=True)


# Global singleton instance
cfg = PipelineConfig()
cfg.ensure_directories()
