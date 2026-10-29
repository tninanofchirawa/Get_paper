"""
services/academic/openalex.py - OpenAlex REST API Client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Enforce OpenAlex rate limits (10 req/s).
- Include mailto:{email} User-Agent etiquette and optional api_key header.
- Circuit breaker protection and exponential backoff retry on HTTP 429.
"""

import urllib.parse
import logging
from typing import Optional, Dict, Any, List
import requests

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("OpenAlexClient")

_OPENALEX_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=cfg.OPENALEX_RATE_LIMIT, safety_buffer_seconds=0.02)


class OpenAlexClient:
    """Client for OpenAlex REST API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("OpenAlex API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _OPENALEX_RATE_LIMITER

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": f"AcademicHarvester/4.0 (mailto:{cfg.POLITE_EMAIL})",
            "Accept": "application/json"
        }
        if cfg.OPENALEX_API_KEY:
            headers["api_key"] = cfg.OPENALEX_API_KEY
        return headers

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Verifies metadata for a DOI against OpenAlex."""
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = doi.strip()
        url = f"{self.BASE_URL}/works/https://doi.org/{urllib.parse.quote(clean_doi)}"

        self.limiter.acquire()

        def _do_request():
            return self.session.get(url, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="OpenAlex"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                location = data.get("primary_location") or {}
                source = location.get("source") or {}

                is_oa = bool(data.get("open_access", {}).get("is_oa", False))
                pdf_url = data.get("open_access", {}).get("oa_url") or ""

                return {
                    "confirmed": True,
                    "title": data.get("title", ""),
                    "venue": source.get("display_name", ""),
                    "issn_list": source.get("issn", []),
                    "year": str(data.get("publication_year") or ""),
                    "is_oa": is_oa,
                    "pdf_link": pdf_url,
                    "type": data.get("type", "")
                }
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limit exceeded")
                return None
            elif resp.status_code in (401, 403):
                self.circuit_breaker.record_failure(resp.status_code, "Auth error")
                return None

            return None

        except Exception as e:
            logger.warning(f"[OpenAlex] verify_doi failed for '{doi}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None

    def verify_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Verifies metadata for a title against OpenAlex Works API."""
        if not title or self.circuit_breaker.is_tripped():
            return None

        clean_title = title.strip()
        url = f"{self.BASE_URL}/works?filter=title.search:{urllib.parse.quote(clean_title)}&per-page=1"

        self.limiter.acquire()

        def _do_request():
            return self.session.get(url, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="OpenAlex Title"
            )

            if resp is None or resp.status_code != 200:
                if resp is None:
                    self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            results = resp.json().get("results", [])
            if not results:
                return None

            data = results[0]
            matched_title = data.get("title", "")

            from harvester.models import clean_matching_title
            from difflib import SequenceMatcher
            s1 = clean_matching_title(clean_title)
            s2 = clean_matching_title(matched_title)
            if SequenceMatcher(None, s1, s2).ratio() < 0.65:
                return None

            self.circuit_breaker.record_success()
            location = data.get("primary_location") or {}
            source = location.get("source") or {}

            is_oa = bool(data.get("open_access", {}).get("is_oa", False))
            pdf_url = data.get("open_access", {}).get("oa_url") or ""

            raw_doi = data.get("doi", "") or ""
            doi = raw_doi
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]

            return {
                "confirmed": True,
                "title": matched_title,
                "venue": source.get("display_name", ""),
                "issn_list": source.get("issn", []),
                "year": str(data.get("publication_year") or ""),
                "doi": doi,
                "is_oa": is_oa,
                "pdf_link": pdf_url,
                "type": data.get("type", "")
            }
        except Exception as e:
            logger.warning(f"[OpenAlex] verify_title failed for '{title}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None
