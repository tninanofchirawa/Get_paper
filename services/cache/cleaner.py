"""
services/cache/cleaner.py - Automated Maintenance & Nightly Cache Purging Engine.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Automated maintenance routine that clears all temporary API cache files, response caches,
  and transient query artifacts every night at midnight (00:00).
- Cron-compatible standalone entrypoint and scheduled background trigger.
- Manual CLI override flag (--clear-cache / --clean-cache) to flush cache on demand.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional

from config import cfg
from services.cache.ttl import CacheTTLPolicy

logger = logging.getLogger("CacheCleaner")


def purge_stale_cache(
    ttl_seconds: int = CacheTTLPolicy.VERIFICATION_TTL_SECONDS,
    target_dirs: Optional[List[str]] = None
) -> int:
    """
    Inspects cache/, logs/, and temp/ directories and permanently unlinks any file
    whose modification timestamp exceeds the TTL threshold (default: 48 hours).

    Returns:
        int: Number of stale cache files purged.
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
                # Only unlink regular files; preserve directories and .gitkeep files
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

    summary_msg = f"[CACHE CLEANER] Purged {purged_count} stale cache files older than {ttl_seconds/3600:.0f} hours."
    print(f"🧹 {summary_msg}")
    logger.info(summary_msg)
    return purged_count


def purge_nightly_cache(
    target_dirs: Optional[List[str]] = None,
    force_all: bool = False
) -> int:
    """
    Automated maintenance routine that clears all temporary API cache files,
    response caches, and transient query artifacts.
    Runs every night at midnight (00:00) or on-demand via --clear-cache.

    If force_all=True:
        Completely flushes all cache files regardless of age (manual override).
    If force_all=False:
        Evicts all transient query artifacts and cache files older than 24 hours.

    Returns:
        int: Number of cache files purged.
    """
    if target_dirs is None:
        target_dirs = [
            cfg.CACHE_DIR,
            str(cfg.BASE_DIR / "temp"),
        ]

    now = time.time()
    purged_count = 0
    # For nightly cleanup, evict query cache files (>24 hours) or all if forced
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

    summary_msg = f"[NightlyCleaner] {mode_label} finished. Purged {purged_count} files."
    print(f"✅ 🧹 {summary_msg}\n")
    logger.info(summary_msg)
    return purged_count


if __name__ == "__main__":
    force = "--clear-all" in sys.argv or "--force" in sys.argv or "--all" in sys.argv
    purge_nightly_cache(force_all=force)
