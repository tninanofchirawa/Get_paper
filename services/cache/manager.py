"""
services/cache/manager.py - Persistent cache read/write layer with key hashing and TTL validation.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config import cfg
from services.cache.ttl import CacheTTLPolicy

logger = logging.getLogger("CacheManager")


class CacheManager:
    """Manages file-based JSON caching with SHA-256 key hashing and TTL eviction."""

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = CacheTTLPolicy.VERIFICATION_TTL_SECONDS):
        self.cache_dir = Path(cache_dir or cfg.CACHE_DIR)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    @staticmethod
    def hash_key(key: str) -> str:
        """Computes deterministic SHA-256 hash for cache keys."""
        return hashlib.sha256(key.strip().lower().encode("utf-8")).hexdigest()

    def _get_path(self, key_hash: str) -> Path:
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str, max_age_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Retrieves and deserializes cached record if not expired."""
        if not key:
            return None
        kh = self.hash_key(key)
        p = self._get_path(kh)
        if not p.exists():
            self.misses += 1
            return None

        try:
            ttl = max_age_seconds or self.default_ttl
            mtime = p.stat().st_mtime
            if (time.time() - mtime) > ttl:
                # Expired
                self.misses += 1
                try:
                    p.unlink()
                except Exception:
                    pass
                return None

            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.hits += 1
            return data
        except Exception as e:
            logger.warning(f"[CacheManager] Failed to read cache for '{key}': {e}")
            self.misses += 1
            return None

    def set(self, key: str, value: Dict[str, Any]):
        """Persists serializable dictionary to cache."""
        if not key or value is None:
            return
        kh = self.hash_key(key)
        p = self._get_path(kh)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[CacheManager] Failed to write cache for '{key}': {e}")

    def delete(self, key: str):
        """Removes a specific entry from cache."""
        if not key:
            return
        kh = self.hash_key(key)
        p = self._get_path(kh)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
