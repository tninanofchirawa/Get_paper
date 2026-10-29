"""
cache_cleaner.py - Cache Life-Cycle Purging Engine (Backward Compatibility Wrapper).
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to services.cache.cleaner.
"""

from services.cache.cleaner import purge_stale_cache, purge_nightly_cache
from services.cache.ttl import CacheTTLPolicy

CACHE_TTL_SECONDS = CacheTTLPolicy.VERIFICATION_TTL_SECONDS

if __name__ == "__main__":
    purge_stale_cache()
