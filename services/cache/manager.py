"""
services/cache/manager.py - Persistent cache layer with compact schema truncation and LRU size-cap eviction.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Compact 'Data-Only' Schema: Purges raw, multi-megabyte API dumps (reference graphs, author profiles)
  storing only downstream verified fields.
- Strict LRU Size-Capped Eviction: Enforces MAX_CACHE_SIZE_MB (default: 30 MB).
  Automatically evicts oldest cache records when the ceiling is exceeded.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import cfg
from services.cache.ttl import CacheTTLPolicy

logger = logging.getLogger("CacheManager")

MAX_CACHE_SIZE_MB: float = float(os.getenv("MAX_CACHE_SIZE_MB", "30.0"))


def truncate_to_compact_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Truncates arbitrary raw API payloads from Semantic Scholar, OpenAlex, or Crossref
    into a standardized, lightweight 'data-only' payload.
    Eliminates multi-megabyte reference lists, full author graphs, and telemetry dumps.
    """
    if not isinstance(data, dict):
        return {}

    # Extract year safely
    raw_year = data.get("year", "")
    if isinstance(raw_year, int):
        clean_yr = raw_year
    elif str(raw_year).isdigit():
        clean_yr = int(raw_year)
    else:
        clean_yr = str(raw_year)

    compact = {
        "doi": str(data.get("doi") or data.get("clean_doi") or "").strip().lower(),
        "title": str(data.get("title") or "").strip(),
        "year": clean_yr,
        "venue": str(data.get("venue") or data.get("journal") or "").strip(),
        "indexed_scopus": bool(data.get("indexed_scopus") or data.get("scopus") or False),
        "indexed_wos": bool(data.get("indexed_wos") or data.get("wos") or False),
        "open_access_url": str(data.get("open_access_url") or data.get("oa_url") or data.get("pdf_link") or "").strip()
    }

    # Retain optional compact downstream flags if present
    if "ieee" in data or "indexed_ieee" in data:
        compact["indexed_ieee"] = bool(data.get("indexed_ieee") or data.get("ieee"))
    if "verified_sources" in data:
        compact["verified_sources"] = list(data["verified_sources"])
    if "citation_count" in data:
        compact["citation_count"] = int(data.get("citation_count") or 0)

    return compact


class CacheManager:
    """
    Manages file-based JSON caching with SHA-256 key hashing,
    compact schema serialization, and strict LRU size-capped eviction.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl: int = CacheTTLPolicy.VERIFICATION_TTL_SECONDS,
        max_size_mb: float = MAX_CACHE_SIZE_MB
    ):
        self.cache_dir = Path(cache_dir or cfg.CACHE_DIR)
        self.default_ttl = default_ttl
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
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
        """Retrieves and deserializes cached record if not expired, updating access time."""
        if not key:
            return None
        kh = self.hash_key(key)
        p = self._get_path(kh)
        if not p.exists():
            self.misses += 1
            return None

        try:
            ttl = max_age_seconds or self.default_ttl
            stat = p.stat()
            now = time.time()
            if (now - stat.st_mtime) > ttl:
                # Expired
                self.misses += 1
                try:
                    p.unlink()
                except Exception:
                    pass
                return None

            # Touch access time for LRU tracking
            try:
                os.utime(p, (now, stat.st_mtime))
            except Exception:
                pass

            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.hits += 1
            return data
        except Exception as e:
            logger.warning(f"[CacheManager] Failed to read cache for '{key}': {e}")
            self.misses += 1
            return None

    def set(self, key: str, value: Dict[str, Any], auto_truncate: bool = True):
        """
        Persists dictionary to cache in compact format and enforces directory size ceiling.
        """
        if not key or value is None:
            return

        # Purge raw API payload dumps down to compact schema
        payload = truncate_to_compact_payload(value) if auto_truncate else value

        kh = self.hash_key(key)
        p = self._get_path(kh)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

            # Enforce size ceiling
            self.enforce_size_cap()
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

    def get_total_cache_size_bytes(self) -> int:
        """Calculates total byte size of regular files in the cache directory."""
        total = 0
        if not self.cache_dir.exists():
            return 0
        for item in self.cache_dir.rglob("*.json"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except Exception:
                    pass
        return total

    def enforce_size_cap(self, max_bytes: Optional[int] = None) -> int:
        """
        Strict LRU size-capped eviction.
        When cache directory exceeds max_bytes, drops the least recently accessed/modified
        entries regardless of age until strictly within ceiling.
        Returns number of evicted files.
        """
        ceiling = max_bytes if max_bytes is not None else self.max_size_bytes
        if not self.cache_dir.exists():
            return 0

        files: List[Path] = []
        for item in self.cache_dir.rglob("*.json"):
            if item.is_file() and item.name != ".gitkeep":
                files.append(item)

        total_bytes = sum(f.stat().st_size for f in files if f.exists())
        if total_bytes <= ceiling:
            return 0

        # Sort files by oldest access/mtime first (LRU order)
        def _get_lru_time(p: Path) -> float:
            try:
                st = p.stat()
                return getattr(st, "st_atime", st.st_mtime)
            except Exception:
                return 0.0

        files.sort(key=_get_lru_time)

        evicted_count = 0
        for f in files:
            if total_bytes <= ceiling:
                break
            try:
                size = f.stat().st_size
                f.unlink()
                total_bytes -= size
                evicted_count += 1
                logger.debug(f"[CacheManager] LRU Evicted: {f.name} ({size/1024:.1f} KB)")
            except Exception as e:
                logger.warning(f"[CacheManager] Could not evict {f.name}: {e}")

        if evicted_count > 0:
            logger.info(
                f"[CacheManager] LRU Size-Cap Eviction: dropped {evicted_count} files. "
                f"New cache size: {total_bytes / (1024*1024):.2f} MB / {ceiling / (1024*1024):.1f} MB cap."
            )
        return evicted_count
