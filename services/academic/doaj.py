"""
services/academic/doaj.py - Directory of Open Access Journals (DOAJ) REST API Client.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import urllib.parse
import logging
from typing import Optional, Dict, Any, List
import requests

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("DoajClient")

# Polite rate limiting for public DOAJ REST API
_DOAJ_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=5.0, safety_buffer_seconds=0.05)


class DoajClient:
    """Client for Directory of Open Access Journals (DOAJ) REST API."""

    BASE_URL = "https://doaj.org/api/v3/search/articles"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("DOAJ API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _DOAJ_RATE_LIMITER

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": f"AcademicHarvester/4.0 (mailto:{cfg.POLITE_EMAIL})",
            "Accept": "application/json"
        }

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Verifies DOI against DOAJ articles search."""
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = doi.strip()
        query_str = f'bibjson.identifier.id:"{clean_doi}"'
        url = f"{self.BASE_URL}/{urllib.parse.quote(query_str)}"

        self.limiter.acquire()

        def _do_request():
            return self.session.get(url, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="DOAJ"
            )
            if resp is None or resp.status_code != 200:
                if resp is None:
                    self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            self.circuit_breaker.record_success()
            item = results[0]
            bibjson = item.get("bibjson", {})
            journal = bibjson.get("journal", {})
            venue = journal.get("title", "")
            issn_list = journal.get("issns", [])
            links = bibjson.get("link", [])
            pdf_link = ""
            for l in links:
                if l.get("type") in ("fulltext", "pdf"):
                    pdf_link = l.get("url", "")
                    break

            return {
                "confirmed": True,
                "title": bibjson.get("title", ""),
                "venue": venue,
                "issn_list": issn_list,
                "year": str(bibjson.get("year") or ""),
                "doi": clean_doi,
                "is_oa": True,
                "pdf_link": pdf_link
            }
        except Exception as e:
            logger.warning(f"[DOAJ] verify_doi failed for '{doi}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None

    def verify_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Verifies title against DOAJ articles search."""
        if not title or self.circuit_breaker.is_tripped():
            return None

        clean_t = title.strip()
        words = clean_t.split()[:8]
        query_str = f'bibjson.title:"{" ".join(words)}"'
        url = f"{self.BASE_URL}/{urllib.parse.quote(query_str)}"

        self.limiter.acquire()

        def _do_request():
            return self.session.get(url, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="DOAJ Title"
            )
            if resp is None or resp.status_code != 200:
                if resp is None:
                    self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            item = results[0]
            bibjson = item.get("bibjson", {})
            matched_title = bibjson.get("title", "")

            from harvester.models import clean_matching_title
            from difflib import SequenceMatcher
            if SequenceMatcher(None, clean_matching_title(clean_t), clean_matching_title(matched_title)).ratio() < 0.70:
                return None

            self.circuit_breaker.record_success()
            journal = bibjson.get("journal", {})
            venue = journal.get("title", "")
            issn_list = journal.get("issns", [])
            links = bibjson.get("link", [])
            pdf_link = ""
            for l in links:
                if l.get("type") in ("fulltext", "pdf"):
                    pdf_link = l.get("url", "")
                    break

            doi = ""
            for ident in bibjson.get("identifier", []):
                if ident.get("type") == "doi":
                    doi = ident.get("id", "")
                    break

            return {
                "confirmed": True,
                "title": matched_title,
                "venue": venue,
                "issn_list": issn_list,
                "year": str(bibjson.get("year") or ""),
                "doi": doi,
                "is_oa": True,
                "pdf_link": pdf_link
            }
        except Exception as e:
            logger.warning(f"[DOAJ] verify_title failed for '{title}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None
