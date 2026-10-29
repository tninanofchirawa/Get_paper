"""
harvester/core_ac.py - Asynchronous CORE (core.ac.uk) API v3 Harvester.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import logging
from typing import List, Tuple, Optional, Dict, Any
import aiohttp

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester

logger = logging.getLogger("CoreHarvester")


class CoreHarvester(BaseAsyncHarvester):
    """
    Harvests open access research publications from CORE API v3.
    Provides secondary active aggregator coverage alongside OpenAlex, Crossref, and arXiv.
    """

    def __init__(self):
        super().__init__("CORE", rate_limit_per_second=2.0)
        self.base_url = "https://api.core.ac.uk/v3/search/works"
        self.api_key = os.getenv("CORE_API_KEY", "").strip()

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
        limit = min(page_size, 50)

        params: Dict[str, Any] = {
            "q": query,
            "limit": limit,
            "offset": offset
        }

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": cfg.USER_AGENT
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            data = await self.get_json(session, self.base_url, params=params, headers=headers)
            if not data:
                return [], None, False

            results = data.get("results", [])
            total_hits = data.get("totalHits", 0)

            papers: List[Paper] = []
            for item in results:
                title = item.get("title", "")
                if not title:
                    continue

                raw_authors = item.get("authors", [])
                author_names = []
                for a in raw_authors:
                    if isinstance(a, dict):
                        name = a.get("name", "")
                    else:
                        name = str(a)
                    if name:
                        author_names.append(name)
                authors_str = "; ".join(author_names)

                year_str = str(item.get("yearPublished") or "")
                raw_doi = item.get("doi") or ""
                doi = sanitize_doi(raw_doi)

                download_url = item.get("downloadUrl") or ""
                links = item.get("links", [])
                pdf_link = download_url
                if not pdf_link and links:
                    for l in links:
                        if isinstance(l, dict) and l.get("type") == "download":
                            pdf_link = l.get("url", "")
                            break

                paper = Paper(
                    title=title,
                    authors=authors_str,
                    year=year_str,
                    publication_type="Journal Article" if item.get("journals") else "Open Access Paper",
                    venue=str(item.get("publisher") or (item.get("journals")[0] if item.get("journals") else "")),
                    doi=doi,
                    url=f"https://doi.org/{doi}" if doi else (item.get("sourceFulltextUrls", [""])[0] if item.get("sourceFulltextUrls") else ""),
                    pdf_link=pdf_link,
                    source="CORE",
                    abstract=item.get("abstract") or "",
                    open_access=bool(pdf_link or download_url)
                )
                papers.append(paper)

            next_offset = offset + len(results)
            has_more = next_offset < total_hits and len(results) > 0
            return papers, str(next_offset) if has_more else None, has_more

        except Exception as e:
            logger.debug(f"[CORE] fetch_page exception: {e}")
            return [], None, False
