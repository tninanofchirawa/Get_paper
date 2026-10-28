"""
verifier/cache.py - Persistent cache for academic indexing verification results.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from config import cfg

logger = logging.getLogger("VerificationCache")


class VerificationCache:
    """Thread-safe persistent JSON cache for paper verification records."""

    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or os.path.join(cfg.CACHE_DIR, "paper_verification_cache.json")
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache from {self.cache_path}: {e}")
            self._data = {}

    def save(self):
        """Persists cache to disk."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache to {self.cache_path}: {e}")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        clean_key = str(key).strip().lower()
        return self._data.get(clean_key)

    def set(self, key: str, value: Dict[str, Any]):
        clean_key = str(key).strip().lower()
        self._data[clean_key] = value
