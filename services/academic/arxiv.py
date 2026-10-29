"""
services/academic/arxiv.py - arXiv API Client with Polite Pacing and Atom XML Parsing.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Requirements:
- Strict polite delay between requests (3.0s as mandated by arXiv API guidelines).
- Atom XML parsing and preprint status resolution.
- Circuit breaker protection and exponential backoff retry on HTTP 429.
"""

import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
import logging
from typing import Optional, Dict, Any, List
import requests

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger("ArxivClient")

# arXiv policy requires at least 3 seconds between successive requests
_ARXIV_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=1.0 / cfg.ARXIV_RATE_DELAY, safety_buffer_seconds=0.1)


class ArxivClient:
    """Client for arXiv API with Atom XML response parsing."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("arXiv API", failure_threshold=3)
        self.session = requests.Session()
        self.limiter = _ARXIV_RATE_LIMITER

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": f"AcademicHarvester/4.0 (mailto:{cfg.POLITE_EMAIL})",
            "Accept": "application/atom+xml"
        }

    def verify_paper(self, title: str, doi: str = "") -> Optional[Dict[str, Any]]:
        """Queries arXiv by DOI or title to check preprint existence."""
        if self.circuit_breaker.is_tripped():
            return None

        search_query = ""
        if doi:
            clean_doi = doi.strip()
            search_query = f'doi:"{clean_doi}"'
        elif title:
            clean_t = re.sub(r'[^a-zA-Z0-9\s]', ' ', title).strip()
            words = clean_t.split()[:8]
            search_query = f'ti:"{" ".join(words)}"'

        if not search_query:
            return None

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": 1
        }

        self.limiter.acquire()

        def _do_request():
            return self.session.get(self.BASE_URL, params=params, headers=self.get_headers(), timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                service_name="arXiv"
            )

            if resp is None:
                self.circuit_breaker.record_failure(None, "Connection timeout")
                return None

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                root = ET.fromstring(resp.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entry = root.find("atom:entry", ns)
                if entry is None:
                    return None

                title_el = entry.find("atom:title", ns)
                pub_el = entry.find("atom:published", ns)
                id_el = entry.find("atom:id", ns)

                paper_title = title_el.text.strip() if title_el is not None and title_el.text else ""
                published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""

                pdf_link = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_link = link.get("href", "")
                        break

                return {
                    "confirmed": True,
                    "title": paper_title,
                    "venue": "arXiv Preprint",
                    "year": published[:4] if len(published) >= 4 else "",
                    "url": arxiv_url,
                    "pdf_link": pdf_link,
                    "is_preprint": True
                }
            elif resp.status_code == 429:
                self.circuit_breaker.record_failure(429, "Rate limit exceeded")
                return None

            return None

        except Exception as e:
            logger.warning(f"[arXiv] verify_paper failed: {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None
