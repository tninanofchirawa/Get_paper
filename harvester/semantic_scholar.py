"""
harvester/semantic_scholar.py - Asynchronous Semantic Scholar Graph API Harvester.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import asyncio
import time
import aiohttp
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester
from utils.rate_limiters import GLOBAL_SEMANTIC_SCHOLAR_LIMITER


class SemanticScholarHarvester(BaseAsyncHarvester):
    """Harvests literature from Semantic Scholar Graph API with strict 1 RPS serialization."""

    # Class-level lock ensures that across ALL instances (Harvester + Verifier),
    # only 1 request is in-flight or retrying against Semantic Scholar at a time.
    _s2_serial_lock = asyncio.Lock()
    _last_request_ts: float = 0.0
    _MIN_INTERVAL: float = 1.15  # 1.15s safety buffer for strict 1 req/sec rule

    def __init__(self):
        # Pass rate_limit_per_second=1.0 to keep BaseAsyncHarvester happy
        super().__init__("SemanticScholar", rate_limit_per_second=1.0)
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        
        # Safely pull the API key from config (checks multiple common attribute names)
        self.api_key = (
            getattr(cfg, "S2_API_KEY", None)
            or getattr(cfg, "SEMANTIC_SCHOLAR_API_KEY", None)
            or ""
        )

    def _build_headers(self) -> Dict[str, str]:
        """Constructs compliant headers with the Semantic Scholar API key."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "AcademicPaperGetter/2.0 (Research Harvester)"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key.strip()
        return headers

    async def _safe_s2_request(
        self,
        session: aiohttp.ClientSession,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Executes the Semantic Scholar request inside a strict serial lock so
        concurrent workers and retries never overlap or trigger 429 storms.
        """
        headers = self._build_headers()
        max_attempts = 3

        async with self._s2_serial_lock:
            for attempt in range(1, max_attempts + 1):
                # 1. Coordinate with global limiter & enforce minimum time gap
                await GLOBAL_SEMANTIC_SCHOLAR_LIMITER.acquire_async()
                
                elapsed = time.monotonic() - SemanticScholarHarvester._last_request_ts
                if elapsed < self._MIN_INTERVAL:
                    await asyncio.sleep(self._MIN_INTERVAL - elapsed)

                try:
                    SemanticScholarHarvester._last_request_ts = time.monotonic()
                    async with session.get(
                        self.base_url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json()

                        if resp.status == 429:
                            # Hold the lock while cooling down so no other task hammers S2
                            cooldown = 3.0 * attempt
                            print(
                                f"[SemanticScholar] 429 Rate Limit. Holding queue for {cooldown:.1f}s "
                                f"(attempt {attempt}/{max_attempts})..."
                            )
                            await asyncio.sleep(cooldown)
                            continue

                        if resp.status >= 500:
                            await asyncio.sleep(2.0)
                            continue

                        # Client error (e.g., 400 Bad Request / 403 Invalid Key)
                        err_text = await resp.text()
                        print(f"[SemanticScholar] HTTP {resp.status}: {err_text[:120]}")
                        return None

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    print(f"[SemanticScholar] Network timeout/error (attempt {attempt}/{max_attempts}): {exc}")
                    await asyncio.sleep(2.0)

        return None

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        query: str,
        page_token: Optional[str] = None,
        page_size: int = 50,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None
    ) -> Tuple[List[Paper], Optional[str], bool]:
        offset = int(page_token) if (page_token and page_token.isdigit()) else 0
        limit = min(page_size, 100)  # S2 allows up to 100 per page (fewer calls needed!)

        # Semantic Scholar standard search caps offset + limit at 1,000
        if offset + limit >= 1000:
            return [], None, False

        params: Dict[str, Any] = {
            "query": query,
            "offset": offset,
            "limit": limit,
            "fields": "title,authors,year,venue,externalIds,abstract,openAccessPdf,publicationTypes"
        }

        if year_range and year_range.lower() != "all years":
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                params["year"] = f"{parts[0]}-{parts[1]}"
            elif len(parts) == 1:
                params["year"] = parts[0]

        # Execute via the serialized, rate-protected request handler
        data = await self._safe_s2_request(session, params=params)
        if not data:
            return [], None, False

        total = data.get("total", 0)
        items = data.get("data") or []

        papers: List[Paper] = []
        for it in items:
            if not isinstance(it, dict):
                continue

            title = (it.get("title") or "").strip()
            if not title:
                continue

            authors_list = it.get("authors") or []
            authors = "; ".join(
                a.get("name", "") for a in authors_list if isinstance(a, dict) and a.get("name")
            )
            year_str = str(it.get("year") or "")
            venue = (it.get("venue") or "").strip()

            external_ids = it.get("externalIds") or {}
            raw_doi = external_ids.get("DOI") or ""
            doi = sanitize_doi(raw_doi)
            arxiv_id = external_ids.get("ArXiv")

            landing_url = (
                f"https://doi.org/{doi}"
                if doi
                else (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "")
            )

            oa_pdf = it.get("openAccessPdf") or {}
            pdf_link = oa_pdf.get("url") or ""

            paper = Paper(
                title=title,
                authors=authors,
                year=year_str,
                publication_type="Journal Article" if venue else "Preprint",
                venue=venue,
                doi=doi,
                url=landing_url,
                pdf_link=pdf_link,
                source="Semantic Scholar",
                abstract=it.get("abstract") or "",
                open_access=bool(pdf_link)
            )
            papers.append(paper)

        next_offset = offset + len(items)
        has_more = (next_offset < total) and (next_offset < 1000) and (len(items) > 0)
        return papers, str(next_offset) if has_more else None, has_more