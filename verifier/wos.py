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
    """Verifies paper indexing against Clarivate Web of Science API."""

    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker
        self.base_url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
        self.session = requests.Session()

    def verify_doi(self, doi: str) -> Optional[bool]:
        """Queries WoS API for given canonical DOI. Returns True/False or None on circuit trip."""
        if self.circuit_breaker.is_tripped() or not cfg.WOS_API_KEY:
            return None

        clean_doi = doi.strip()
        params = {"q": f"DO={clean_doi}", "limit": 1}
        headers = cfg.get_http_headers("wos")

        try:
            resp = self.session.get(self.base_url, params=params, headers=headers, timeout=12)
            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = data.get("metadata", {}).get("total", 0)
                return total > 0
            elif resp.status_code in (401, 403, 429):
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None
            else:
                return False
        except Exception as e:
            self.circuit_breaker.record_failure(None, str(e))
            return None
