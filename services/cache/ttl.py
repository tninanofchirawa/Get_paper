"""
services/cache/ttl.py - TTL policies and expiration constants for cache layers.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from config.constants import CACHE_TTL_SECONDS, CACHE_TTL_HOURS, NIGHTLY_PURGE_HOUR


class CacheTTLPolicy:
    """Configurable TTL policies for distinct cache categories."""

    # Default API verification cache TTL (48 hours)
    VERIFICATION_TTL_SECONDS: int = CACHE_TTL_SECONDS
    VERIFICATION_TTL_HOURS: int = CACHE_TTL_HOURS

    # Transient query and search results cache TTL (24 hours)
    QUERY_CACHE_TTL_SECONDS: int = 24 * 3600

    # Temporary files and download buffer TTL (12 hours)
    TEMP_BUFFER_TTL_SECONDS: int = 12 * 3600

    # Nightly maintenance scheduled hour (00:00 IST)
    MIDNIGHT_PURGE_HOUR: int = NIGHTLY_PURGE_HOUR
