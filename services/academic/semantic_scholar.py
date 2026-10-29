"""
services/academic/semantic_scholar.py - Semantic Scholar Graph API Client with Strict Rate Limiting.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Strict rate limit of 1 request per second (cumulative across all endpoints) with 1.05s safety buffer.
- Exponential backoff retry handler catching HTTP 429 (Too Many Requests).
- Outbound headers must include 'x-api-key': os.getenv('S2_API_KEY') on every outbound request.
- Token pooling and rotation when multiple keys are provided.
"""

import os
import time
import urllib.parse
import logging
from typing import Optional, Dict, Any, List, Tuple
import requests

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter, GLOBAL_SEMANTIC_SCHOLAR_LIMITER
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("SemanticScholarClient")

# Global singleton rate limiter across all Semantic Scholar endpoints:
# Strict 1 request per second with 0.05s safety buffer (1.05s total interval)
_S2_RATE_LIMITER = GLOBAL_SEMANTIC_SCHOLAR_LIMITER


class SemanticScholarClient:
    """
    Client for Semantic Scholar Graph API.
    Enforces strict 1 req/sec pacing, HTTP 429 exponential backoff,
    and mandatory 'x-api-key' header forwarding from S2_API_KEY.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("Semantic Scholar API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _S2_RATE_LIMITER
        self.key_pool: List[str] = cfg.get_key_pool("semantic_scholar")
        self.current_key_idx: int = 0

    def _get_api_key(self) -> str:
        """Retrieves active S2 API key from environment or key pool."""
        env_key = os.getenv("S2_API_KEY")
        if env_key:
            return env_key
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)]
        return cfg.S2_API_KEY

    def _rotate_key(self):
        """Rotates to next key in pool upon receiving rate limit response."""
        if self.key_pool and len(self.key_pool) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.key_pool)
            logger.info(f"[SemanticScholar] Rotated API key (active index: {self.current_key_idx})")

    def get_headers(self) -> Dict[str, str]:
        """Builds outbound headers, strictly enforcing 'x-api-key' when available."""
        headers = {
            "User-Agent": cfg.USER_AGENT,
            "Accept": "application/json",
        }
        api_key = self._get_api_key()
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Verifies citation metadata for a DOI against Semantic Scholar.
        Applies token-bucket pacing and 429 backoff retries.
        """
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = doi.strip()
        url = f"{self.BASE_URL}/paper/{urllib.parse.quote(clean_doi)}"
        params = {"fields": "title,venue,year,externalIds,openAccessPdf"}

        # Strict 1 req/s token bucket pacing
        self.limiter.acquire()

        def _do_request():
            headers = self.get_headers()
            return self.session.get(url, params=params, headers=headers, timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                initial_backoff=1.5,
                service_name="Semantic Scholar"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Timeout or connection error")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                venue = data.get("venue") or ""
                oa = data.get("openAccessPdf") or {}
                return {
                    "confirmed": True,
                    "title": data.get("title", ""),
                    "venue": venue,
                    "year": str(data.get("year") or ""),
                    "pdf_link": oa.get("url", ""),
                    "external_ids": data.get("externalIds", {})
                }
            elif resp.status_code == 429:
                self._rotate_key()
                self.circuit_breaker.record_failure(429, "Rate limited")
                return None
            elif resp.status_code in (401, 403):
                self._rotate_key()
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None

            return None

        except Exception as e:
            logger.warning(f"[SemanticScholar] verify_doi failed for '{doi}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None

    def search_papers(
        self,
        query: str,
        offset: int = 0,
        limit: int = 50,
        year_range: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """
        Searches Semantic Scholar with pagination parameters.
        Returns: (paper_records, total_count, has_more)
        """
        if self.circuit_breaker.is_tripped() or not query:
            return [], 0, False

        url = f"{self.BASE_URL}/paper/search"
        limit = min(limit, 50)
        params: Dict[str, Any] = {
            "query": query,
            "offset": offset,
            "limit": limit,
            "fields": "title,authors,year,venue,externalIds,abstract,openAccessPdf"
        }

        if year_range and year_range.lower() != "all years":
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                params["year"] = f"{parts[0]}-{parts[1]}"
            elif len(parts) == 1:
                params["year"] = parts[0]

        # Enforce strict 1 req/sec pacing
        self.limiter.acquire()

        def _do_request():
            headers = self.get_headers()
            return self.session.get(url, params=params, headers=headers, timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                initial_backoff=1.5,
                service_name="Semantic Scholar Search"
            )

            if resp is None or resp.status_code != 200:
                if resp is not None and resp.status_code == 429:
                    self._rotate_key()
                return [], 0, False

            data = resp.json()
            total = data.get("total", 0)
            items = data.get("data", [])
            has_more = (offset + len(items)) < total and len(items) > 0
            return items, total, has_more

        except Exception as e:
            logger.error(f"[SemanticScholar] search_papers failed: {e}")
            return [], 0, False
