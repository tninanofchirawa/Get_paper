"""
harvester/semantic_scholar.py - Asynchronous Semantic Scholar Graph API Harvester.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import aiohttp
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester


class SemanticScholarHarvester(BaseAsyncHarvester):
    """Harvests literature from Semantic Scholar Graph API."""

    def __init__(self):
        super().__init__("SemanticScholar", rate_limit_per_second=cfg.SEMANTIC_SCHOLAR_RATE_LIMIT)
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

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
            "query": query,
            "offset": offset,
            "limit": limit,
            "fields": "title,authors,year,venue,externalIds,abstract,openAccessPdf"
        }

        if year_range and year_range.lower() != "all years":
            # Semantic scholar supports year parameter e.g. "2021-2026"
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                params["year"] = f"{parts[0]}-{parts[1]}"
            elif len(parts) == 1:
                params["year"] = parts[0]

        data = await self.get_json(session, self.base_url, params=params)
        if not data:
            return [], None, False

        total = data.get("total", 0)
        items = data.get("data", [])

        papers: List[Paper] = []
        for it in items:
            title = it.get("title", "")
            if not title:
                continue

            authors = "; ".join(a.get("name", "") for a in it.get("authors", []) if a.get("name"))
            year_str = str(it.get("year") or "")
            venue = it.get("venue") or ""

            external_ids = it.get("externalIds") or {}
            raw_doi = external_ids.get("DOI") or ""
            doi = sanitize_doi(raw_doi)
            arxiv_id = external_ids.get("ArXiv")

            landing_url = f"https://doi.org/{doi}" if doi else (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "")

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
        has_more = next_offset < total and len(items) > 0
        return papers, str(next_offset) if has_more else None, has_more
