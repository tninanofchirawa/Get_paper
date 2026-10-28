"""
config.py - Centralized configuration, environment loader, and pipeline constants.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional


def load_env_file(env_path: Optional[str] = None):
    """Loads environment variables from .env file into os.environ if present."""
    candidate_paths = [
        env_path,
        ".env",
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    for p in candidate_paths:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break


# Pre-load environment variables
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
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()

    # Local Master Journal Databases (Branch 2 Fallback)
    SCOPUS_LOCAL_DB_PATH: str = os.getenv("SCOPUS_LOCAL_DB_PATH", "data/scopus_source_list.xlsx")
    WOS_LOCAL_DB_PATH: str = os.getenv("WOS_LOCAL_DB_PATH", "data/wos_master_journal_list.csv")

    # 3. Rate Limits & Pacing Controls
    OPENALEX_RATE_LIMIT: float = 10.0        # max req/sec
    CROSSREF_RATE_LIMIT: float = 50.0        # max req/sec (polite pool)
    ARXIV_RATE_DELAY: float = 3.0            # arXiv polite delay between requests (seconds)
    SEMANTIC_SCHOLAR_RATE_LIMIT: float = 5.0 # max req/sec
    SCOPUS_SNAIL_PACE_SECONDS: float = 1.2   # Elsevier Scopus API snail pace delay
    DEFAULT_TIMEOUT: int = int(os.getenv("PAPER_HARVESTER_TIMEOUT", "25"))
    MAX_RETRIES: int = 4
    BACKOFF_FACTOR: float = 1.5

    # 4. Quotas & Operational Limits
    DEFAULT_QUOTA: int = 250
    HARD_CAP_TOPICS: int = 5
    HARD_CAP_SUBTOPICS_PER_TOPIC: int = 5
    HARD_CAP_QUOTA_PER_TOPIC: int = 500

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
    GDRIVE_SERVICE_ACCOUNT_JSON: str = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "service_account.json").strip()
    GDRIVE_SERVICE_ACCOUNT_RAW: str = os.getenv("GDRIVE_SERVICE_ACCOUNT_RAW", "").strip()

    # 7. Paths & Storage
    BASE_DIR: Path = Path(__file__).resolve().parent
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
        elif service == "semantic_scholar":
            if self.SEMANTIC_SCHOLAR_API_KEY:
                headers["x-api-key"] = self.SEMANTIC_SCHOLAR_API_KEY
        return headers

    def ensure_directories(self):
        """Ensures that all application directories exist."""
        for p in [self.INPUT_DIR, self.OUTPUT_DIR, self.CACHE_DIR, self.LOGS_DIR, self.TEMP_DIR, self.CONFIG_DIR, os.path.dirname(self.DATABASE_PATH)]:
            if p:
                os.makedirs(p, exist_ok=True)


# Global singleton instance
cfg = PipelineConfig()
cfg.ensure_directories()
