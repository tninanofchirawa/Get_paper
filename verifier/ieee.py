"""
verifier/ieee.py - IEEE Xplore REST API verifier with circuit breaker.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging
from typing import Optional

import requests

from config import cfg
from verifier.circuit_breaker import CircuitBreaker

logger = logging.getLogger("IEEEVerifier")


class IEEEXploreVerifier:
    """Verifies paper indexing against IEEE Xplore REST API with token pooling."""

    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker
        self.base_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
        self.session = requests.Session()
        self.key_pool = cfg.get_key_pool("ieee")
        self.current_key_idx = 0

    def _rotate_key(self):
        if len(self.key_pool) > 1:
            self.current_key_idx += 1
            logger.info(f"[IEEE] Rotated API key in pool (index {self.current_key_idx % len(self.key_pool)})")

    def _get_api_key(self) -> str:
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)]
        return cfg.IEEE_API_KEY

    def verify_doi(self, doi: str) -> Optional[bool]:
        """Queries IEEE Xplore API for given canonical DOI."""
        api_key = self._get_api_key()
        if self.circuit_breaker.is_tripped() or not api_key:
            return None

        clean_doi = doi.strip()
        params = {"apikey": api_key, "doi": clean_doi, "max_records": 1}

        try:
            resp = self.session.get(self.base_url, params=params, timeout=12)
            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = data.get("total_records", 0)
                return total > 0
            elif resp.status_code in (401, 403, 429):
                self._rotate_key()
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None
            else:
                return False
        except Exception as e:
            self.circuit_breaker.record_failure(None, str(e))
            return None

    def is_ieee_venue(self, venue: str, doi: str = "") -> bool:
        """Heuristic check: returns True if venue or DOI clearly identifies as IEEE."""
        if "10.1109" in doi:
            return True
        v = venue.lower()
        return "ieee" in v or "institute of electrical and electronics" in v
