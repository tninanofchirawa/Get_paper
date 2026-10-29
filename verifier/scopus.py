"""
verifier/scopus.py - Elsevier Scopus Search API verifier with snail pace and circuit breaker.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import urllib.parse
import logging
from typing import Optional, Dict, Any

import requests

from config import cfg
from verifier.circuit_breaker import CircuitBreaker

logger = logging.getLogger("ScopusVerifier")


class ScopusVerifier:
    """Verifies paper indexing against Elsevier Scopus Search API with token pooling."""

    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker
        self.last_query_time = 0.0
        self.session = requests.Session()
        self.key_pool = cfg.get_key_pool("elsevier")
        self.current_key_idx = 0

    def _rotate_key(self):
        if len(self.key_pool) > 1:
            self.current_key_idx += 1
            logger.info(f"[Scopus] Rotated API key in pool (index {self.current_key_idx % len(self.key_pool)})")

    def _get_api_key(self) -> str:
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)]
        return cfg.ELSEVIER_API_KEY

    def _wait_snail_pace(self):
        """Enforces minimum 1.2s delay strictly for Scopus queries."""
        elapsed = time.time() - self.last_query_time
        if elapsed < cfg.SCOPUS_SNAIL_PACE_SECONDS:
            time.sleep(cfg.SCOPUS_SNAIL_PACE_SECONDS - elapsed)
        self.last_query_time = time.time()

    def verify_doi(self, doi: str) -> Optional[bool]:
        """Queries Scopus API for given canonical DOI. Returns True/False or None on error/trip."""
        if self.circuit_breaker.is_tripped():
            return None

        if not cfg.ELSEVIER_API_KEY or not cfg.ELSEVIER_INST_TOKEN:
            self.circuit_breaker.record_failure(401, "Missing API Key or Institutional Token")
            return None

        self._wait_snail_pace()
        clean_doi = doi.strip()
        query = f'DOI("{clean_doi}")'
        url = f"https://api.elsevier.com/content/search/scopus?query={urllib.parse.quote(query)}&count=1"

        headers = cfg.get_http_headers("scopus")
        headers["X-ELS-APIKey"] = self._get_api_key()

        try:
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = int(data.get("search-results", {}).get("opensearch:totalResults", "0"))
                return total > 0
            elif resp.status_code in (401, 403, 429):
                self._rotate_key()
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None
            else:
                logger.debug(f"[Scopus] Non-200 status {resp.status_code} for DOI {clean_doi}")
                return False
        except Exception as e:
            self.circuit_breaker.record_failure(None, str(e))
            return None

    def verify_title(self, title: str) -> Optional[bool]:
        """Queries Scopus API for given title as fallback if DOI is absent."""
        if self.circuit_breaker.is_tripped() or not title:
            return None

        self._wait_snail_pace()
        clean_title = title.replace('"', '').strip()
        query = f'TITLE("{clean_title}")'
        url = f"https://api.elsevier.com/content/search/scopus?query={urllib.parse.quote(query)}&count=1"

        headers = cfg.get_http_headers("scopus")
        try:
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = int(data.get("search-results", {}).get("opensearch:totalResults", "0"))
                return total > 0
            elif resp.status_code in (401, 403, 429):
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None
            else:
                return False
        except Exception as e:
            self.circuit_breaker.record_failure(None, str(e))
            return None
