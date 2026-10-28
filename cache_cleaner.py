"""
cache_cleaner.py - Automated 48-Hour Cache Life-Cycle Purging Engine.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import cfg

logger = logging.getLogger("CacheCleaner")

# Hard-cap TTL at 48 hours (172,800 seconds)
CACHE_TTL_SECONDS = 48 * 3600  # 172,800s


def purge_stale_cache(
    ttl_seconds: int = CACHE_TTL_SECONDS,
    target_dirs: Optional[List[str]] = None
) -> int:
    """
    Inspects cache/, logs/, and temp/ directories and permanently unlinks any file
    whose modification timestamp exceeds the 48-hour TTL threshold.

    Returns:
        int: Number of stale cache files purged.
    """
    if target_dirs is None:
        target_dirs = [
            cfg.CACHE_DIR,
            cfg.LOGS_DIR,
            os.path.join(str(cfg.BASE_DIR), "temp"),
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
                # Only unlink regular files; skip directories and .gitkeep files
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

    summary_msg = f"[CACHE CLEANER] Purged {purged_count} stale cache files older than 48 hours."
    print(f"🧹 {summary_msg}")
    logger.info(summary_msg)
    return purged_count


if __name__ == "__main__":
    purge_stale_cache()
