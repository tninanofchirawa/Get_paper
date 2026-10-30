"""
services/academic/semantic_scholar.py - Semantic Scholar Graph API Client with Strict Rate Limiting.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Strict rate limit of 1 request per second (cumulative across all endpoints) with 1.05s safety buffer.
- Exponential backoff retry handler catching HTTP 429 (Too Many Requests).
- Outbound headers must include 'x-api-key': os.getenv('S2_API_KEY') on every outbound request.
- Token pooling and rotation when multiple keys are provided via on_retry_callback.
"""

import os
import urllib.parse
import logging
from typing import Optional, Dict, Any, List, Tuple
from difflib import SequenceMatcher
import requests

from config import cfg
from utils.rate_limiters import GLOBAL_SEMANTIC_SCHOLAR_LIMITER
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker
from harvester.models import clean_matching_title, sanitize_doi

logger = logging.getLogger("SemanticScholarClient")

_S2_RATE_LIMITER = GLOBAL_SEMANTIC_SCHOLAR_LIMITER


class SemanticScholarClient:
    """
    Client for Semantic Scholar Graph API.
    Enforces strict 1 req/sec pacing, HTTP 429 exponential backoff with key rotation callbacks,
    and mandatory 'x-api-key' header forwarding.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("Semantic Scholar API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _S2_RATE_LIMITER
        self.key_pool: List[str] = getattr(cfg, "get_key_pool", lambda service: [])("semantic_scholar")
        self.current_key_idx: int = 0
        self.last_status_code: Optional[int] = None
        self.on_429_callback: Optional[Any] = None

    def _get_api_key(self) -> str:
        """Retrieves active S2 API key from key pool first, falling back to env/config."""
        if self.key_pool and len(self.key_pool) > 1:
            return self.key_pool[self.current_key_idx % len(self.key_pool)].strip()
        
        env_key = (
            os.getenv("S2_API_KEY") 
            or (self.key_pool[0] if self.key_pool else "")
            or getattr(cfg, "S2_API_KEY", None) 
            or getattr(cfg, "SEMANTIC_SCHOLAR_API_KEY", None) 
            or ""
        )
        return env_key.strip()

    def _rotate_key(self) -> None:
        """Rotates to next key in pool upon receiving rate limit or auth response."""
        if self.key_pool and len(self.key_pool) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.key_pool)
            logger.info(f"[SemanticScholar] Rotated API key (active index: {self.current_key_idx})")

    def _handle_retry_callback(self, resp: requests.Response, attempt: int) -> None:
        """
        Callback passed to execute_with_429_retry.
        Fires on HTTP 429 or auth errors to rotate credentials before the next attempt.
        """
        if resp.status_code in (429, 401, 403):
            self._rotate_key()

        if resp.status_code == 429 and self.on_429_callback:
            try:
                self.on_429_callback()
            except Exception as e:
                logger.warning(f"[SemanticScholar] on_429_callback raised an exception: {e}")

    def get_headers(self) -> Dict[str, str]:
        """Builds outbound headers, forwarding 'x-api-key' dynamically from the rotated pool."""
        headers = {
            "User-Agent": getattr(cfg, "USER_AGENT", "AcademicHarvester/4.0"),
            "Accept": "application/json",
        }
        api_key = self._get_api_key()
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Verifies citation metadata for a DOI against Semantic Scholar.
        Applies token-bucket pacing on every attempt and properly formats the DOI prefix.
        """
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = sanitize_doi(doi)
        if not clean_doi:
            return None

        # Keep forward slashes unencoded so path-based DOI routing resolves correctly
        encoded_id = f"DOI:{urllib.parse.quote(clean_doi, safe='/')}"
        url = f"{self.BASE_URL}/paper/{encoded_id}"
        params = {"fields": "title,venue,year,externalIds,openAccessPdf"}

        def _do_request() -> requests.Response:
            self.limiter.acquire()
            headers = self.get_headers()
            return self.session.get(url, params=params, headers=headers, timeout=getattr(cfg, "DEFAULT_TIMEOUT", 10))

        try:
            # Scale retries up to key pool size if multiple keys are available
            max_retries = max(getattr(cfg, "MAX_RETRIES", 3), len(self.key_pool))

            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=max_retries,
                initial_backoff=2.0,
                service_name="Semantic Scholar",
                on_retry_callback=self._handle_retry_callback
            )

            if resp is None:
                self.last_status_code = None
                self.circuit_breaker.record_failure(None, "Timeout or connection error")
                return None

            self.last_status_code = resp.status_code

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
            elif resp.status_code == 404:
                return None
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limited across all keys")
                return None
            elif resp.status_code in (401, 403):
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
        Searches Semantic Scholar with pagination parameters and automatic key rotation on 429.
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

        def _do_request() -> requests.Response:
            self.limiter.acquire()
            headers = self.get_headers()
            return self.session.get(url, params=params, headers=headers, timeout=getattr(cfg, "DEFAULT_TIMEOUT", 10))

        try:
            max_retries = max(getattr(cfg, "MAX_RETRIES", 3), len(self.key_pool))

            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=max_retries,
                initial_backoff=2.0,
                service_name="Semantic Scholar Search",
                on_retry_callback=self._handle_retry_callback
            )

            if resp is None:
                self.last_status_code = None
                self.circuit_breaker.record_failure(None, "Search request timeout or error")
                return [], 0, False

            self.last_status_code = resp.status_code

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                total = data.get("total", 0)
                items = data.get("data", [])
                has_more = (offset + len(items)) < total and len(items) > 0
                return items, total, has_more
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Search rate limited across all keys")
                return [], 0, False
            elif resp.status_code in (401, 403):
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return [], 0, False

            return [], 0, False

        except Exception as e:
            logger.error(f"[SemanticScholar] search_papers failed: {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return [], 0, False

    def verify_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Verifies metadata for a title against Semantic Scholar Graph API."""
        if not title or self.circuit_breaker.is_tripped():
            return None

        items, _, _ = self.search_papers(query=title, limit=1)
        if not items:
            return None

        data = items[0]
        matched_title = data.get("title", "")
        
        s1 = clean_matching_title(title)
        s2 = clean_matching_title(matched_title)
        if SequenceMatcher(None, s1, s2).ratio() < 0.65:
            return None

        venue = data.get("venue") or ""
        oa = data.get("openAccessPdf") or {}
        ext_ids = data.get("externalIds") or {}
        doi = sanitize_doi(ext_ids.get("DOI", ""))

        return {
            "confirmed": True,
            "title": matched_title,
            "venue": venue,
            "year": str(data.get("year") or ""),
            "doi": doi,
            "pdf_link": oa.get("url", ""),
            "external_ids": ext_ids
        }