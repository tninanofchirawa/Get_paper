"""
services/academic/crossref.py - Crossref REST API Client with Polite Pool Etiquette.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Enforce polite pool rate limits (up to 50 req/s polite pool).
- Send User-Agent header with mailto:{email} etiquette.
- Circuit breaker protection and exponential backoff retry on HTTP 429.
"""

import urllib.parse
import logging
from typing import Optional, Dict, Any, List, Tuple
import requests

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("CrossrefClient")

_CROSSREF_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=cfg.CROSSREF_RATE_LIMIT, safety_buffer_seconds=0.01)


class CrossrefClient:
    """Client for Crossref REST API with polite pool acceleration."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("Crossref API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _CROSSREF_RATE_LIMITER

    def get_headers(self) -> Dict[str, str]:
        """Builds polite pool headers with email address."""
        headers = {
            "User-Agent": f"AcademicHarvester/4.0 (mailto:{cfg.POLITE_EMAIL})",
            "Accept": "application/json"
        }
        return headers

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Verifies metadata for a DOI against Crossref."""
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = doi.strip()
        url = f"{self.BASE_URL}/{urllib.parse.quote(clean_doi)}"

        self.limiter.acquire()

        def _do_request():
            return self.session.get(url, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="Crossref"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                item = resp.json().get("message", {})
                titles = item.get("title", [])
                title = titles[0] if titles else ""
                containers = item.get("container-title", [])
                venue = containers[0] if containers else ""
                issn_list = item.get("ISSN", [])

                issued = item.get("issued", {}).get("date-parts", [[]])[0]
                year = str(issued[0]) if issued else ""

                return {
                    "confirmed": True,
                    "title": title,
                    "venue": venue,
                    "year": year,
                    "issn_list": issn_list,
                    "type": item.get("type", "")
                }
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limit exceeded")
                return None
            elif resp.status_code in (401, 403):
                self.circuit_breaker.record_failure(resp.status_code, "Auth error")
                return None

            return None

        except Exception as e:
            logger.warning(f"[Crossref] verify_doi failed for '{doi}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None
