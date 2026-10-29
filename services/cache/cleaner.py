"""
services/cache/cleaner.py - Automated Maintenance, LRU Size-Capped Eviction & Nightly Purge.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Nightly Purge (00:00 Maintenance): Automatically clears transient API query artifacts,
  response cache dumps, and temporary files at midnight every night.
- Size-Capped LRU Eviction: Enforces MAX_CACHE_SIZE_MB (default 30 MB), evicting oldest
  entries regardless of age when the local cache directory ceiling is breached.
- Manual CLI Override: Supports --clear-cache / --clean-cache on demand.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional

from config import cfg
from services.cache.ttl import CacheTTLPolicy
from services.cache.manager import CacheManager, MAX_CACHE_SIZE_MB

logger = logging.getLogger("CacheCleaner")


def enforce_lru_cache_size_cap(
    cache_dir: Optional[str] = None,
    max_size_mb: float = MAX_CACHE_SIZE_MB
) -> int:
    """
    Enforces the strict size-capped LRU eviction manager on the cache directory.
    When directory size exceeds max_size_mb, drops the oldest records until within ceiling.
    """
    mgr = CacheManager(cache_dir=cache_dir, max_size_mb=max_size_mb)
    return mgr.enforce_size_cap()


def purge_stale_cache(
    ttl_seconds: int = CacheTTLPolicy.VERIFICATION_TTL_SECONDS,
    target_dirs: Optional[List[str]] = None,
    max_size_mb: float = MAX_CACHE_SIZE_MB
) -> int:
    """
    Inspects cache/, logs/, and temp/ directories:
    1. Unlinks files exceeding TTL (default: 48 hours).
    2. Applies strict LRU size-capped eviction if cache exceeds max_size_mb (30 MB).
    """
    if target_dirs is None:
        target_dirs = [
            cfg.CACHE_DIR,
            cfg.LOGS_DIR,
            str(cfg.BASE_DIR / "temp"),
        ]

    now = time.time()
    purged_count = 0

    for dir_path in target_dirs:
        p = Path(dir_path)
        if not p.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            continue

        try:
            for item in p.rglob("*"):
                # Preserve directories and .gitkeep files
                if item.is_file() and item.name != ".gitkeep":
                    try:
                        mtime = os.path.getmtime(item)
                        age_seconds = now - mtime
                        if age_seconds > ttl_seconds:
                            item.unlink()
                            purged_count += 1
                            logger.debug(f"[CACHE CLEANER] Deleted stale file '{item.name}' (age: {age_seconds/3600:.1f}h)")
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        logger.warning(f"[CACHE CLEANER] Could not unlink '{item}': {e}")
        except Exception as e:
            logger.warning(f"[CACHE CLEANER] Error inspecting directory '{dir_path}': {e}")

    # Enforce LRU size cap on cache directory
    lru_evicted = enforce_lru_cache_size_cap(cache_dir=cfg.CACHE_DIR, max_size_mb=max_size_mb)
    purged_count += lru_evicted

    summary_msg = f"[CACHE CLEANER] Purged {purged_count} stale/oversized cache files."
    print(f"🧹 {summary_msg}")
    logger.info(summary_msg)
    return purged_count


def purge_nightly_cache(
    target_dirs: Optional[List[str]] = None,
    force_all: bool = False,
    max_size_mb: float = MAX_CACHE_SIZE_MB
) -> int:
    """
    Automated nightly maintenance routine executing at midnight (00:00).
    Clears temporary API cache files, response caches, and transient query artifacts.
    Enforces the 30 MB LRU size cap across all runs.
    """
    if target_dirs is None:
        target_dirs = [
            cfg.CACHE_DIR,
            str(cfg.BASE_DIR / "temp"),
        ]

    now = time.time()
    purged_count = 0
    cutoff_seconds = 0 if force_all else CacheTTLPolicy.QUERY_CACHE_TTL_SECONDS

    mode_label = "Complete Cache Flush" if force_all else "Automated Nightly Purge (00:00 Maintenance)"
    print(f"\n🌙 [Cache Maintenance] Executing {mode_label}...")

    for dir_path in target_dirs:
        p = Path(dir_path)
        if not p.exists():
            continue

        try:
            for item in p.rglob("*"):
                if item.is_file() and item.name != ".gitkeep":
                    try:
                        if force_all:
                            item.unlink()
                            purged_count += 1
                        else:
                            mtime = os.path.getmtime(item)
                            if (now - mtime) >= cutoff_seconds:
                                item.unlink()
                                purged_count += 1
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        logger.warning(f"[NightlyCleaner] Could not remove '{item}': {e}")
        except Exception as e:
            logger.warning(f"[NightlyCleaner] Error inspecting directory '{dir_path}': {e}")

    if not force_all:
        lru_evicted = enforce_lru_cache_size_cap(cache_dir=cfg.CACHE_DIR, max_size_mb=max_size_mb)
        purged_count += lru_evicted

    summary_msg = f"[NightlyCleaner] {mode_label} finished. Purged {purged_count} files."
    print(f"✅ 🧹 {summary_msg}\n")
    logger.info(summary_msg)
    return purged_count


if __name__ == "__main__":
    force = "--clear-all" in sys.argv or "--force" in sys.argv or "--all" in sys.argv
    purge_nightly_cache(force_all=force)
