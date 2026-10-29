"""
scripts/maintenance/cache_cleaner.py - Cache Life-Cycle Purging Engine.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to services.cache.cleaner.
"""

import sys
from pathlib import Path

# Dynamic project root path resolution
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.cache.cleaner import purge_stale_cache, purge_nightly_cache
from services.cache.ttl import CacheTTLPolicy

CACHE_TTL_SECONDS = CacheTTLPolicy.VERIFICATION_TTL_SECONDS

if __name__ == "__main__":
    force = "--force" in sys.argv or "--all" in sys.argv
    if force:
        purge_nightly_cache(force_all=True)
    else:
        purge_stale_cache()
