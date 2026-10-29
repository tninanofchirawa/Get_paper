"""
verifier/dual_branch.py - Multi-source academic verification engine.
Executes concurrent querying across arXiv, OpenAlex, Crossref, Scopus, Clarivate Web of Science,
and IEEE Xplore with circuit breakers, token pooling, polite rate limiting, and persistent caching.
Supports strict Scopus/WoS indexing filtering and comprehensive Open Access fallbacks.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import json
import logging
import concurrent.futures
from typing import List, Optional, Dict, Any, Tuple

from config import cfg
from harvester.models import Paper
from verifier.circuit_breaker import CircuitBreaker
from verifier.local_matcher import LocalDBMatcher
from verifier.cache import VerificationCache
from verifier.scopus import ScopusVerifier
from verifier.wos import WebOfScienceVerifier
from verifier.ieee import IEEEXploreVerifier
from verifier.openalex_verifier import OpenAlexVerifier
from verifier.crossref_verifier import CrossrefVerifier
from verifier.arxiv_verifier import ArxivVerifier
from verifier.semantic_scholar_verifier import SemanticScholarVerifier
from verifier.doaj_verifier import DoajVerifier
from verifier.tiered_verifier import TieredWorkloadVerifier

logger = logging.getLogger("DualBranchVerifier")


class DualBranchVerifier:
    """
    Coordinates multi-source academic citation verification across:
      - Institutional: Elsevier Scopus, Clarivate WoS, IEEE Xplore
      - Open Aggregators: Crossref, OpenAlex, arXiv, Semantic Scholar
      - Offline Databases: Scopus & WoS Master Journal Lists (ISSN O(1) matching)
    Executes provider queries concurrently to maximize pipeline throughput.
    """

    def __init__(
        self,
        local_db: Optional[LocalDBMatcher] = None,
        cache: Optional[VerificationCache] = None,
        inst_token_flag: bool = True,
        max_workers: int = 6
    ):
        self.inst_token_flag = inst_token_flag and cfg.has_institutional_credentials
        self.local_db = local_db or LocalDBMatcher()
        self.cache = cache or VerificationCache()
        self.max_workers = max_workers
        self.last_excluded_count = 0

        # Circuit breakers for network APIs
        self.scopus_cb = CircuitBreaker("Elsevier Scopus", failure_threshold=2)
        self.wos_cb = CircuitBreaker("Clarivate WoS", failure_threshold=2)
        self.ieee_cb = CircuitBreaker("IEEE Xplore", failure_threshold=2)
        self.crossref_cb = CircuitBreaker("Crossref", failure_threshold=3)
        self.openalex_cb = CircuitBreaker("OpenAlex", failure_threshold=3)
        self.arxiv_cb = CircuitBreaker("arXiv", failure_threshold=3)
        self.s2_cb = CircuitBreaker("Semantic Scholar", failure_threshold=3)
        self.doaj_cb = CircuitBreaker("DOAJ", failure_threshold=3)

        # Verifier clients
        self.scopus_verifier = ScopusVerifier(self.scopus_cb)
        self.wos_verifier = WebOfScienceVerifier(self.wos_cb)
        self.ieee_verifier = IEEEXploreVerifier(self.ieee_cb)
        self.openalex_verifier = OpenAlexVerifier(self.local_db)
        self.crossref_verifier = CrossrefVerifier(self.crossref_cb)
        self.arxiv_verifier = ArxivVerifier(self.arxiv_cb)
        self.semantic_scholar_verifier = SemanticScholarVerifier(self.s2_cb)
        self.doaj_verifier = DoajVerifier(self.doaj_cb)

        # Tiered partitioned workload verifier
        self.tiered_verifier = TieredWorkloadVerifier(
            semantic_scholar_verifier=self.semantic_scholar_verifier,
            openalex_verifier=self.openalex_verifier,
            crossref_verifier=self.crossref_verifier,
            arxiv_verifier=self.arxiv_verifier,
            doaj_verifier=self.doaj_verifier,
            local_db=self.local_db,
            cache=self.cache
        )

    def get_circuit_status(self) -> Dict[str, str]:
        """Returns the operational status of all verification sources."""
        return {
            "Elsevier Scopus": self.scopus_cb.status_summary,
            "Clarivate WoS": self.wos_cb.status_summary,
            "IEEE Xplore": self.ieee_cb.status_summary,
            "Crossref": self.crossref_cb.status_summary,
            "OpenAlex": self.openalex_cb.status_summary,
            "arXiv": self.arxiv_cb.status_summary,
            "Semantic Scholar": self.s2_cb.status_summary,
            "DOAJ": self.doaj_cb.status_summary,
            "Local DB Matcher": "Active (Offline ISSN Set Intersection)"
        }

    def verify_paper(self, paper: Paper) -> Paper:
        """
        Executes concurrent multi-source verification for a single paper.
        Updates indexing flags, Open Access metadata, and populated Verified Sources list in-place.
        """
        doi = paper.clean_doi or paper.doi
        cache_key = doi or paper.clean_title

        # 1. Check persistent cache for O(1) resolution
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached:
                paper.scopus_indexed = cached.get("scopus")
                paper.wos_indexed = cached.get("wos")
                paper.ieee_indexed = cached.get("ieee")
                paper.open_access = cached.get("open_access", paper.open_access)
                paper.verification_source = cached.get("source", "Cache")
                paper.verified_sources = cached.get("verified_sources", [])
                if not paper.verified_sources and paper.verification_source:
                    paper.verified_sources = [s.strip() for s in paper.verification_source.split(",") if s.strip()]
                return paper

        # 2. Local offline DB checks (fastest, 0 network overhead)
        local_scopus_hit = None
        local_wos_hit = None
        if paper.issn_list:
            local_scopus_hit = self.local_db.is_scopus_issn(paper.issn_list)
            local_wos_hit = self.local_db.is_wos_issn(paper.issn_list)

        # Heuristic IEEE check
        heuristic_ieee = self.ieee_verifier.is_ieee_venue(paper.venue, doi)

        # 3. Concurrent verification task runners
        def check_scopus():
            if local_scopus_hit is True:
                return "scopus", True, "Local Scopus DB"
            if self.inst_token_flag and not self.scopus_cb.is_tripped() and cfg.has_scopus_credentials:
                res = self.scopus_verifier.verify_doi(doi) if doi else self.scopus_verifier.verify_title(paper.title)
                if res is not None:
                    return "scopus", res, "Scopus API"
            return "scopus", local_scopus_hit, "Local Scopus DB" if local_scopus_hit else None

        def check_wos():
            if local_wos_hit is True:
                return "wos", True, "Local WoS DB"
            if self.inst_token_flag and not self.wos_cb.is_tripped() and cfg.WOS_API_KEY and doi:
                res = self.wos_verifier.verify_doi(doi)
                if res is not None:
                    return "wos", res, "WoS API"
            return "wos", local_wos_hit, "Local WoS DB" if local_wos_hit else None

        def check_ieee():
            if not self.ieee_cb.is_tripped() and cfg.IEEE_API_KEY and doi:
                res = self.ieee_verifier.verify_doi(doi)
                if res is not None:
                    return "ieee", res, "IEEE API"
            return "ieee", heuristic_ieee if heuristic_ieee else None, "IEEE Venue" if heuristic_ieee else None

        def check_crossref():
            if not self.crossref_cb.is_tripped():
                res = self.crossref_verifier.verify_doi(doi) if doi else self.crossref_verifier.verify_title(paper.title)
                return "crossref", res, "Crossref"
            return "crossref", None, None

        def check_openalex():
            if not self.openalex_cb.is_tripped() and doi:
                res = self.openalex_verifier.check_work(doi)
                return "openalex", res, "OpenAlex"
            return "openalex", None, None

        def check_arxiv():
            if not self.arxiv_cb.is_tripped():
                res = self.arxiv_verifier.verify_paper(doi=doi, title=paper.title, url=paper.url)
                return "arxiv", res, "arXiv"
            return "arxiv", None, None

        def check_semantic_scholar():
            if not self.s2_cb.is_tripped() and not self.tiered_verifier.safety_valve.is_paused and doi:
                res = self.semantic_scholar_verifier.verify_doi(doi)
                return "semantic_scholar", res, "Semantic Scholar"
            return "semantic_scholar", None, None

        def check_doaj():
            if not self.doaj_cb.is_tripped():
                res = self.doaj_verifier.verify_doi(doi) if doi else self.doaj_verifier.verify_title(paper.title)
                return "doaj", res, "DOAJ"
            return "doaj", None, None

        tasks = [
            check_scopus,
            check_wos,
            check_ieee,
            check_crossref,
            check_openalex,
            check_arxiv,
            check_semantic_scholar,
            check_doaj
        ]

        verified_sources_list: List[str] = []
        raw_results: Dict[str, Any] = {}

        # Query all providers concurrently without degrading pipeline throughput
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_provider = {executor.submit(fn): fn.__name__ for fn in tasks}
            for future in concurrent.futures.as_completed(future_to_provider):
                try:
                    prov, result, label = future.result()
                    raw_results[prov] = (result, label)
                except Exception as e:
                    logger.debug(f"Verification worker error: {e}")

        # 4. Synthesize provider confirmations & enrich metadata
        # A. Scopus
        scopus_res, scopus_label = raw_results.get("scopus", (None, None))
        if scopus_res is True:
            paper.scopus_indexed = True
            verified_sources_list.append("Scopus")

        # B. Web of Science
        wos_res, wos_label = raw_results.get("wos", (None, None))
        if wos_res is True:
            paper.wos_indexed = True
            verified_sources_list.append("Web of Science")

        # C. IEEE Xplore
        ieee_res, ieee_label = raw_results.get("ieee", (None, None))
        if ieee_res is True:
            paper.ieee_indexed = True
            verified_sources_list.append("IEEE Xplore")

        # D. Crossref
        cr_data, _ = raw_results.get("crossref", (None, None))
        if cr_data and cr_data.get("confirmed"):
            verified_sources_list.append("Crossref")
            if not paper.venue and cr_data.get("venue"):
                paper.venue = cr_data["venue"]
            if not paper.doi and cr_data.get("doi"):
                paper.doi = cr_data["doi"]

        # E. OpenAlex CC0 Registry Fallback
        oa_data, _ = raw_results.get("openalex", (None, None))
        if oa_data and oa_data.get("found"):
            verified_sources_list.append("OpenAlex")
            if oa_data.get("is_scopus_indexed") and not paper.scopus_indexed:
                paper.scopus_indexed = True
                if "Scopus" not in verified_sources_list:
                    verified_sources_list.append("Scopus")
            if oa_data.get("is_wos_indexed") and not paper.wos_indexed:
                paper.wos_indexed = True
                if "Web of Science" not in verified_sources_list:
                    verified_sources_list.append("Web of Science")
            if oa_data.get("is_oa"):
                paper.open_access = True
            if oa_data.get("oa_url") and not paper.pdf_link:
                paper.pdf_link = oa_data["oa_url"]
            if not paper.venue and oa_data.get("journal"):
                paper.venue = oa_data["journal"]

        # F. arXiv Preprints
        arxiv_data, _ = raw_results.get("arxiv", (None, None))
        if arxiv_data and arxiv_data.get("confirmed"):
            verified_sources_list.append("arXiv")
            paper.open_access = True
            if not paper.pdf_link and arxiv_data.get("pdf_link"):
                paper.pdf_link = arxiv_data["pdf_link"]
            # Preprints fallback: classify publication type as Preprint unless peer-reviewed venue confirmed
            if not paper.scopus_indexed and not paper.wos_indexed and not (cr_data and cr_data.get("is_peer_reviewed")):
                paper.publication_type = "Preprint"

        # G. Semantic Scholar
        s2_data, _ = raw_results.get("semantic_scholar", (None, None))
        if s2_data and s2_data.get("confirmed"):
            verified_sources_list.append("Semantic Scholar")
            if not paper.venue and s2_data.get("venue"):
                paper.venue = s2_data["venue"]
            if not paper.pdf_link and s2_data.get("pdf_link"):
                paper.pdf_link = s2_data["pdf_link"]

        # H. DOAJ
        doaj_data, _ = raw_results.get("doaj", (None, None))
        if doaj_data and doaj_data.get("confirmed"):
            verified_sources_list.append("DOAJ")
            paper.open_access = True
            if not paper.venue and doaj_data.get("venue"):
                paper.venue = doaj_data["venue"]
            if not paper.pdf_link and doaj_data.get("pdf_link"):
                paper.pdf_link = doaj_data["pdf_link"]

        # 5. Open Access Fallback verification
        # When Scopus and WoS are absent: ensure DOIs, preprint statuses, and venues are verified
        if not paper.scopus_indexed and not paper.wos_indexed:
            if paper.pdf_link or (oa_data and oa_data.get("is_oa")) or (arxiv_data and arxiv_data.get("confirmed")) or (doaj_data and doaj_data.get("confirmed")):
                paper.open_access = True
            elif "open access" in paper.access_type.lower():
                paper.open_access = True

        # Ensure boolean defaults
        if paper.scopus_indexed is None:
            paper.scopus_indexed = False
        if paper.wos_indexed is None:
            paper.wos_indexed = False
        if paper.ieee_indexed is None:
            paper.ieee_indexed = False
        if paper.open_access is None:
            paper.open_access = bool(paper.pdf_link or "open access" in paper.access_type.lower())

        # Deduplicate verified sources while retaining order
        seen = set()
        deduped_sources = []
        for s in verified_sources_list:
            if s not in seen:
                seen.add(s)
                deduped_sources.append(s)

        paper.verified_sources = deduped_sources
        paper.verification_source = ", ".join(deduped_sources) if deduped_sources else "Open Access Fallback"

        # Explicit Verified_Via tracking
        if not paper.verified_via or paper.verified_via == "Unverified":
            if "OpenAlex" in deduped_sources:
                paper.verified_via = "OpenAlex"
            elif "Crossref" in deduped_sources:
                paper.verified_via = "Crossref"
            elif "Semantic Scholar" in deduped_sources:
                paper.verified_via = "Semantic_Scholar"
            elif "arXiv" in deduped_sources:
                paper.verified_via = "arXiv"
            elif "DOAJ" in deduped_sources:
                paper.verified_via = "DOAJ"
            else:
                paper.verified_via = "Unverified"

        # 6. Save in persistent cache
        if cache_key:
            self.cache.set(cache_key, {
                "scopus": paper.scopus_indexed,
                "wos": paper.wos_indexed,
                "ieee": paper.ieee_indexed,
                "open_access": paper.open_access,
                "source": paper.verification_source,
                "verified_sources": paper.verified_sources,
                "verified_via": paper.verified_via
            })

        return paper

    def filter_indexed_papers(self, papers: List[Paper]) -> Tuple[List[Paper], int]:
        """
        Strict indexing filter: retains ONLY papers indexed in Scopus or Web of Science.
        Returns: (retained_papers, excluded_count)
        """
        retained: List[Paper] = []
        excluded_count = 0

        for p in papers:
            if p.scopus_indexed is True or p.wos_indexed is True:
                retained.append(p)
            else:
                excluded_count += 1

        return retained, excluded_count

    def verify_batch(
        self,
        papers: List[Paper],
        only_indexed: bool = False,
        progress_callback: Optional[Any] = None
    ) -> List[Paper]:
        """
        Verifies a list of candidate papers using 3-way workload partitioning
        across Semantic Scholar, OpenAlex, and Crossref with automatic sequential fallback ring
        and arXiv/DOAJ catch-all.
        If institutional credentials are enabled, institutional APIs (Scopus/WoS/IEEE) are evaluated.
        If only_indexed is True, selectively retains only papers indexed in Scopus or Web of Science.
        """
        if not papers:
            self.last_excluded_count = 0
            return []

        # If institutional credentials exist, check institutional APIs for candidates
        if self.inst_token_flag:
            for p in papers:
                doi = p.clean_doi or p.doi
                if not self.scopus_cb.is_tripped() and cfg.has_scopus_credentials:
                    res = self.scopus_verifier.verify_doi(doi) if doi else None
                    if res is True:
                        p.scopus_indexed = True
                        if "Scopus" not in p.verified_sources:
                            p.verified_sources.append("Scopus")
                if not self.wos_cb.is_tripped() and cfg.WOS_API_KEY and doi:
                    res = self.wos_verifier.verify_doi(doi)
                    if res is True:
                        p.wos_indexed = True
                        if "Web of Science" not in p.verified_sources:
                            p.verified_sources.append("Web of Science")
                if not self.ieee_cb.is_tripped() and cfg.IEEE_API_KEY and doi:
                    res = self.ieee_verifier.verify_doi(doi)
                    if res is True:
                        p.ieee_indexed = True
                        if "IEEE Xplore" not in p.verified_sources:
                            p.verified_sources.append("IEEE Xplore")

        # Three-way partitioned aggregator verification with tiered fallback
        verified = self.tiered_verifier.verify_batch(papers, progress_callback=progress_callback)

        self.cache.save()

        if only_indexed:
            retained, excluded = self.filter_indexed_papers(verified)
            self.last_excluded_count = excluded
            print(f"🎯 [Indexed-Only Filter] Retained {len(retained)} Scopus/WoS indexed papers (Excluded {excluded} non-indexed).")
            return retained

        self.last_excluded_count = 0
        return verified
