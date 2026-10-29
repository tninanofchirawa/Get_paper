"""
config/constants.py - Pipeline constants, rate limits, and operational thresholds.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

# Operational Quotas and Caps
DEFAULT_QUOTA: int = 250
HARD_CAP_TOPICS: int = 5
HARD_CAP_SUBTOPICS_PER_TOPIC: int = 5
HARD_CAP_QUOTA_PER_TOPIC: int = 500

# Rate Limits (Requests per second / polite delay)
OPENALEX_RATE_LIMIT: float = 10.0         # max req/sec
CROSSREF_RATE_LIMIT: float = 50.0         # max req/sec (polite pool)
ARXIV_RATE_DELAY: float = 3.0             # arXiv polite delay between requests (seconds)
SEMANTIC_SCHOLAR_RATE_LIMIT: float = 1.0  # STRICT rate limit of 1 req/sec cumulative
SCOPUS_SNAIL_PACE_SECONDS: float = 1.2    # Elsevier Scopus API snail pace delay

# Network & Resilience Defaults
DEFAULT_TIMEOUT: int = 25
MAX_RETRIES: int = 4
BACKOFF_FACTOR: float = 1.5

# Cache & Storage Defaults
CACHE_TTL_HOURS: int = 48
CACHE_TTL_SECONDS: int = 48 * 3600
NIGHTLY_PURGE_HOUR: int = 0  # 00:00 midnight
