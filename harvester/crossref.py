"""
harvester/crossref.py - Asynchronous Crossref Harvester with offset/cursor pagination.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import aiohttp
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester


class CrossrefHarvester(BaseAsyncHarvester):
    """Harvests peer-reviewed publications from Crossref REST API."""

    def __init__(self):
        super().__init__("Crossref", rate_limit_per_second=cfg.CROSSREF_RATE_LIMIT)
        self.base_url = "https://api.crossref.org/works"

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
        rows = min(page_size, 100)

        params: Dict[str, Any] = {
            "query": query,
            "rows": rows,
            "offset": offset
        }

        # Polite pool header email
        if cfg.POLITE_EMAIL:
            params["mailto"] = cfg.POLITE_EMAIL

        # Filters
        filters = []
        if year_range and year_range.lower() != "all years":
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                filters.append(f"from-pub-date:{parts[0]}-01-01,until-pub-date:{parts[1]}-12-31")
            elif len(parts) == 1:
                filters.append(f"from-pub-date:{parts[0]}-01-01,until-pub-date:{parts[0]}-12-31")

        if doc_filter:
            doc_lower = doc_filter.lower()
            if "journal" in doc_lower:
                filters.append("type:journal-article")
            elif "conference" in doc_lower:
                filters.append("type:proceedings-article")

        if filters:
            params["filter"] = ",".join(filters)

        data = await self.get_json(session, self.base_url, params=params)
        if not data:
            return [], None, False

        message = data.get("message", {})
        total_results = message.get("total-results", 0)
        items = message.get("items", [])

        papers: List[Paper] = []
        for it in items:
            titles = it.get("title", [])
            title = titles[0] if titles else ""
            if not title:
                continue

            # Authors
            authors_list = []
            for a in it.get("author", []):
                family = a.get("family", "").strip()
                given = a.get("given", "").strip()
                if family and given:
                    authors_list.append(f"{family}, {given}")
                elif family:
                    authors_list.append(family)
            authors_str = "; ".join(authors_list)

            # Year
            date_parts = (
                it.get("published", {}).get("date-parts") or
                it.get("published-print", {}).get("date-parts") or
                it.get("published-online", {}).get("date-parts") or
                it.get("issued", {}).get("date-parts") or
                it.get("created", {}).get("date-parts")
            )
            year_str = str(date_parts[0][0]) if (date_parts and date_parts[0]) else ""

            # Venue & ISSNs
            containers = it.get("container-title", [])
            venue = containers[0] if containers else ""
            issns = it.get("ISSN") or []

            # DOI & Landing URL
            doi = sanitize_doi(it.get("DOI") or "")
            landing_url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")

            # Publication Type
            raw_type = it.get("type", "")
            pub_type = "Journal Article"
            if "proceedings" in raw_type or "conference" in raw_type:
                pub_type = "Conference Paper"
            elif "book" in raw_type:
                pub_type = "Book Chapter"
            elif "posted-content" in raw_type:
                pub_type = "Preprint"

            # Check for direct PDF in links
            pdf_link = ""
            for lk in it.get("link", []):
                if lk.get("content-type") == "application/pdf":
                    pdf_link = lk.get("URL", "")
                    break

            # Abstract
            abstract = it.get("abstract", "")

            paper = Paper(
                title=title,
                authors=authors_str,
                year=year_str,
                publication_type=pub_type,
                venue=venue,
                doi=doi,
                url=landing_url,
                pdf_link=pdf_link,
                source="Crossref",
                abstract=abstract,
                issn_list=issns
            )
            papers.append(paper)

        next_offset = offset + len(items)
        has_more = next_offset < total_results and len(items) > 0
        return papers, str(next_offset) if has_more else None, has_more
