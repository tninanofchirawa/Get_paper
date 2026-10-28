"""
harvester/openalex.py - Asynchronous OpenAlex Harvester with cursor-based pagination.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import aiohttp
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester


class OpenAlexHarvester(BaseAsyncHarvester):
    """Harvests academic papers from OpenAlex with cursor-based deep pagination."""

    def __init__(self):
        super().__init__("OpenAlex", rate_limit_per_second=cfg.OPENALEX_RATE_LIMIT)
        self.base_url = "https://api.openalex.org/works"

    @staticmethod
    def _reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
        """Reconstructs text from OpenAlex's abstract_inverted_index."""
        if not inverted_index:
            return ""
        positions = {}
        for word, idxs in inverted_index.items():
            for idx in idxs:
                positions[idx] = word
        sorted_words = [positions[i] for i in sorted(positions.keys())]
        return " ".join(sorted_words)

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        query: str,
        page_token: Optional[str] = None,
        page_size: int = 50,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None
    ) -> Tuple[List[Paper], Optional[str], bool]:
        cursor = page_token or "*"
        params = {
            "search": query,
            "per_page": min(page_size, 100),
            "cursor": cursor
        }

        # Build OpenAlex filter string
        filters = []
        if year_range and year_range.lower() != "all years":
            # Check for pattern like "2021-2026" or single year
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                filters.append(f"from_publication_date:{parts[0]}-01-01,to_publication_date:{parts[1]}-12-31")
            elif len(parts) == 1:
                filters.append(f"publication_year:{parts[0]}")

        if doc_filter:
            doc_lower = doc_filter.lower()
            if "journal" in doc_lower:
                filters.append("type:article")
            elif "conference" in doc_lower:
                filters.append("type:proceedings-article")
            elif "preprint" in doc_lower:
                filters.append("type:preprint")

        if filters:
            params["filter"] = ",".join(filters)

        data = await self.get_json(session, self.base_url, params=params)
        if not data:
            return [], None, False

        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        results = data.get("results", [])

        papers: List[Paper] = []
        for item in results:
            title = item.get("display_name") or item.get("title") or ""
            if not title:
                continue

            # Authors
            authors_list = []
            for authorship in item.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name")
                if name:
                    authors_list.append(name)
            authors_str = "; ".join(authors_list)

            # Year
            year_str = str(item.get("publication_year") or "")

            # Venue & Publisher
            primary_loc = item.get("primary_location") or {}
            source_obj = primary_loc.get("source") or {}
            venue = source_obj.get("display_name") or ""
            issns = source_obj.get("issn") or []

            # DOI & Landing URL
            doi = sanitize_doi(item.get("doi") or "")
            landing_url = primary_loc.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else "")

            # PDF link
            pdf_link = (item.get("open_access") or {}).get("oa_url") or primary_loc.get("pdf_url") or ""

            # Publication Type
            raw_type = item.get("type", "article")
            pub_type = "Journal Article"
            if raw_type in ("proceedings-article", "proceedings"):
                pub_type = "Conference Paper"
            elif raw_type in ("book-chapter", "book"):
                pub_type = "Book Chapter"
            elif raw_type == "preprint":
                pub_type = "Preprint"

            # Open Access status
            is_oa = (item.get("open_access") or {}).get("is_oa") is True

            # Abstract
            abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))

            paper = Paper(
                title=title,
                authors=authors_str,
                year=year_str,
                publication_type=pub_type,
                venue=venue,
                doi=doi,
                url=landing_url,
                pdf_link=pdf_link,
                source="OpenAlex",
                abstract=abstract,
                access_type="Open Access" if is_oa else "Closed",
                issn_list=issns,
                open_access=is_oa
            )
            papers.append(paper)

        has_more = bool(next_cursor and len(results) > 0)
        return papers, next_cursor, has_more
