"""
harvester/arxiv.py - Asynchronous arXiv Atom Harvester with rate-limit compliance.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi, clean_year
from harvester.base import BaseAsyncHarvester


class ArxivHarvester(BaseAsyncHarvester):
    """Harvests open-access preprint papers from the arXiv Atom XML API."""

    def __init__(self):
        # arXiv enforces maximum 1 request per 3 seconds
        super().__init__("arXiv", rate_limit_per_second=1.0 / cfg.ARXIV_RATE_DELAY)
        self.base_url = "http://export.arxiv.org/api/query"

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        query: str,
        page_token: Optional[str] = None,
        page_size: int = 50,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None
    ) -> Tuple[List[Paper], Optional[str], bool]:
        # Skip if doc_filter specifically requests Journal Articles Only
        if doc_filter and "journal articles only" in doc_filter.lower():
            return [], None, False

        start = int(page_token) if (page_token and page_token.isdigit()) else 0
        max_results = min(page_size, 50)

        # Build clean search query for arXiv
        clean_query = " AND ".join(f'all:"{word.strip()}"' for word in query.split() if len(word.strip()) > 2)
        if not clean_query:
            clean_query = f'all:"{query}"'

        params = {
            "search_query": clean_query,
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }

        req_headers = {"User-Agent": cfg.USER_AGENT}
        await self.limiter.acquire()

        try:
            async with session.get(self.base_url, params=params, headers=req_headers, timeout=aiohttp.ClientTimeout(total=cfg.DEFAULT_TIMEOUT)) as resp:
                if resp.status != 200:
                    return [], None, False
                xml_data = await resp.text()
        except Exception:
            return [], None, False

        try:
            root = ET.fromstring(xml_data)
        except Exception:
            return [], None, False

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom"
        }

        entries = root.findall("atom:entry", ns)
        papers: List[Paper] = []

        for entry in entries:
            title_tag = entry.find("atom:title", ns)
            title = " ".join(title_tag.text.split()) if (title_tag is not None and title_tag.text) else ""
            if not title:
                continue

            # Authors
            author_names = []
            for author_tag in entry.findall("atom:author", ns):
                name_tag = author_tag.find("atom:name", ns)
                if name_tag is not None and name_tag.text:
                    author_names.append(name_tag.text.strip())
            authors_str = "; ".join(author_names)

            # Year
            published_tag = entry.find("atom:published", ns)
            year_str = clean_year(published_tag.text[:4]) if (published_tag is not None and published_tag.text) else ""

            # Year filter check
            if year_range and year_range.lower() != "all years" and year_str:
                parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
                if len(parts) == 2 and not (parts[0] <= year_str <= parts[1]):
                    continue
                elif len(parts) == 1 and year_str != parts[0]:
                    continue

            # Links
            landing_url = ""
            pdf_link = ""
            for link_tag in entry.findall("atom:link", ns):
                rel = link_tag.attrib.get("rel")
                link_type = link_tag.attrib.get("type")
                href = link_tag.attrib.get("href", "")
                if rel == "alternate" and href:
                    landing_url = href
                if link_type == "application/pdf" or "pdf" in href:
                    pdf_link = href

            # DOI
            doi_tag = entry.find("arxiv:doi", ns)
            doi = sanitize_doi(doi_tag.text) if (doi_tag is not None and doi_tag.text) else ""

            # Abstract
            summary_tag = entry.find("atom:summary", ns)
            abstract = " ".join(summary_tag.text.split()) if (summary_tag is not None and summary_tag.text) else ""

            # Journal Ref
            jref_tag = entry.find("arxiv:journal_ref", ns)
            venue = jref_tag.text.strip() if (jref_tag is not None and jref_tag.text) else "arXiv Preprint"

            paper = Paper(
                title=title,
                authors=authors_str,
                year=year_str,
                publication_type="Preprint",
                venue=venue,
                doi=doi,
                url=landing_url,
                pdf_link=pdf_link,
                source="arXiv",
                abstract=abstract,
                access_type="Open Access",
                open_access=True
            )
            papers.append(paper)

        next_start = start + len(entries)
        has_more = len(entries) >= max_results
        return papers, str(next_start) if has_more else None, has_more
