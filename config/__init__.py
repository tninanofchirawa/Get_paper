"""
config - Centralized configuration, environment loader, and pipeline constants package.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

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
    CACHE_TTL_HOURS,
    CACHE_TTL_SECONDS,
    NIGHTLY_PURGE_HOUR,
)
from config.settings import PipelineConfig, cfg

__all__ = [
    "load_env_file",
    "PipelineConfig",
    "cfg",
    "DEFAULT_QUOTA",
    "HARD_CAP_TOPICS",
    "HARD_CAP_SUBTOPICS_PER_TOPIC",
    "HARD_CAP_QUOTA_PER_TOPIC",
    "OPENALEX_RATE_LIMIT",
    "CROSSREF_RATE_LIMIT",
    "ARXIV_RATE_DELAY",
    "SEMANTIC_SCHOLAR_RATE_LIMIT",
    "SCOPUS_SNAIL_PACE_SECONDS",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "BACKOFF_FACTOR",
    "CACHE_TTL_HOURS",
    "CACHE_TTL_SECONDS",
    "NIGHTLY_PURGE_HOUR",
]
