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
from typing import Optional, Dict, Any
import requests

from config import cfg
from harvester.models import sanitize_doi, clean_matching_title
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("OpenAlexClient")

# Note: If Code A and Code B run in the same process, consider passing a single 
# shared TokenBucketRateLimiter to both to strictly enforce the 10 req/s global limit.
_OPENALEX_RATE_LIMITER = TokenBucketRateLimiter(
    rate_limit_per_second=cfg.OPENALEX_RATE_LIMIT, 
    safety_buffer_seconds=0.02
)

class OpenAlexClient:
    """Client for OpenAlex REST API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("OpenAlex API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _OPENALEX_RATE_LIMITER

    def get_headers(self) -> Dict[str, str]:
        """Construct headers to ensure inclusion in the OpenAlex polite pool."""
        headers = {
            "User-Agent": f"AcademicHarvester/4.0 (mailto:{cfg.POLITE_EMAIL})",
            "Accept": "application/json"
        }
        if getattr(cfg, "OPENALEX_API_KEY", None):
            headers["api_key"] = cfg.OPENALEX_API_KEY
        return headers

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Verifies metadata for a DOI against OpenAlex."""
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = sanitize_doi(doi)
        if not clean_doi:
            return None
            
        url = f"{self.BASE_URL}/works/https://doi.org/{urllib.parse.quote(clean_doi, safe='/')}"

        def _do_request():
            self.limiter.acquire()
            return self.session.get(url, headers=self.get_headers(), timeout=getattr(cfg, 'DEFAULT_TIMEOUT', 10))

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=getattr(cfg, 'MAX_RETRIES', 3),
                service_name="OpenAlex"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Connection timeout or max retries exceeded")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                location = data.get("primary_location") or {}
                source = location.get("source") or {}

                open_access_data = data.get("open_access") or {}
                is_oa = bool(open_access_data.get("is_oa", False))
                pdf_url = open_access_data.get("oa_url") or ""

                return {
                    "confirmed": True,
                    "title": data.get("title", ""),
                    "venue": source.get("display_name", ""),
                    "issn_list": source.get("issn", []),
                    "year": str(data.get("publication_year") or ""),
                    "doi": clean_doi,
                    "is_oa": is_oa,
                    "pdf_link": pdf_url,
                    "type": data.get("type", "")
                }
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limit exceeded")
                return None
            elif resp.status_code in (401, 403):
                self.circuit_breaker.record_failure(resp.status_code, "Authentication/Authorization error")
                return None
            elif resp.status_code == 404:
                # DOI not found in OpenAlex; not a circuit breaker failure, just missing data
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

        def _do_request():
            self.limiter.acquire()
            return self.session.get(url, headers=self.get_headers(), timeout=getattr(cfg, 'DEFAULT_TIMEOUT', 10))

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=getattr(cfg, 'MAX_RETRIES', 3),
                service_name="OpenAlex Title"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Connection timeout or max retries exceeded")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limit exceeded")
                return None
            elif resp.status_code in (401, 403):
                self.circuit_breaker.record_failure(resp.status_code, "Authentication/Authorization error")
                return None
            else:
                return None

            results = resp.json().get("results", [])
            if not results:
                return None

            data = results[0]
            matched_title = data.get("title", "")

            # Fuzzy match to ensure the search result actually matches the requested title
            from difflib import SequenceMatcher
            
            s1 = clean_matching_title(clean_title)
            s2 = clean_matching_title(matched_title)
            if SequenceMatcher(None, s1, s2).ratio() < 0.65:
                return None

            location = data.get("primary_location") or {}
            source = location.get("source") or {}

            open_access_data = data.get("open_access") or {}
            is_oa = bool(open_access_data.get("is_oa", False))
            pdf_url = open_access_data.get("oa_url") or ""

            raw_doi = data.get("doi", "") or ""
            doi = sanitize_doi(raw_doi)

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