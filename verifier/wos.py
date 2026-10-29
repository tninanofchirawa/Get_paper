"""
verifier/wos.py - Clarivate Web of Science (WoS) API verifier with circuit breaker.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging
from typing import Optional

import requests

from config import cfg
from verifier.circuit_breaker import CircuitBreaker

logger = logging.getLogger("WoSVerifier")


class WebOfScienceVerifier:
    """Verifies paper indexing against Clarivate Web of Science API with token pooling."""

    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker
        self.base_url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
        self.session = requests.Session()
        self.key_pool = cfg.get_key_pool("wos")
        self.current_key_idx = 0

    def _rotate_key(self):
        if len(self.key_pool) > 1:
            self.current_key_idx += 1
            logger.info(f"[WoS] Rotated API key in pool (index {self.current_key_idx % len(self.key_pool)})")

    def _get_api_key(self) -> str:
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)]
        return cfg.WOS_API_KEY

    def verify_doi(self, doi: str) -> Optional[bool]:
        """Queries WoS API for given canonical DOI. Returns True/False or None on circuit trip."""
        api_key = self._get_api_key()
        if self.circuit_breaker.is_tripped() or not api_key:
            return None

        clean_doi = doi.strip()
        params = {"q": f"DO={clean_doi}", "limit": 1}
        headers = cfg.get_http_headers("wos")
        headers["X-ApiKey"] = api_key

        try:
            resp = self.session.get(self.base_url, params=params, headers=headers, timeout=12)
            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = data.get("metadata", {}).get("total", 0)
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
