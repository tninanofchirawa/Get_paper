"""
verifier/dual_branch.py - Dual-branch verification engine with circuit breakers and fallback.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging
from typing import List, Optional, Dict, Any

from config import cfg
from harvester.models import Paper
from verifier.circuit_breaker import CircuitBreaker
from verifier.local_db import LocalDBMatcher
from verifier.cache import VerificationCache
from verifier.scopus import ScopusVerifier
from verifier.wos import WebOfScienceVerifier
from verifier.ieee import IEEEXploreVerifier
from verifier.openalex_verifier import OpenAlexVerifier

logger = logging.getLogger("DualBranchVerifier")


class DualBranchVerifier:
    """
    Coordinates Branch 1 (Institutional tokens) and Branch 2 (Open Access / local DB) verification.
    If institutional API throws 401/403 or 429, circuit trips immediately and falls back to Branch 2.
    """

    def __init__(
        self,
        local_db: Optional[LocalDBMatcher] = None,
        cache: Optional[VerificationCache] = None,
        inst_token_flag: bool = True
    ):
        self.inst_token_flag = inst_token_flag and cfg.has_institutional_credentials
        self.local_db = local_db or LocalDBMatcher()
        self.cache = cache or VerificationCache()

        # Circuit breakers for Branch 1
        self.scopus_cb = CircuitBreaker("Elsevier Scopus", failure_threshold=2)
        self.wos_cb = CircuitBreaker("Clarivate WoS", failure_threshold=2)
        self.ieee_cb = CircuitBreaker("IEEE Xplore", failure_threshold=2)

        # Verifier clients
        self.scopus_verifier = ScopusVerifier(self.scopus_cb)
        self.wos_verifier = WebOfScienceVerifier(self.wos_cb)
        self.ieee_verifier = IEEEXploreVerifier(self.ieee_cb)
        self.openalex_verifier = OpenAlexVerifier(self.local_db)

    def get_circuit_status(self) -> Dict[str, str]:
        """Returns the operational status of all verification branches."""
        return {
            "Elsevier Scopus": self.scopus_cb.status_summary,
            "Clarivate WoS": self.wos_cb.status_summary,
            "IEEE Xplore": self.ieee_cb.status_summary,
            "Branch 2 OpenAlex/Local": "Active (CC0 Open Registry & Offline Hash Matching)"
        }

    def verify_paper(self, paper: Paper) -> Paper:
        """
        Executes dual-branch verification for a single paper, updating indexing flags in-place.
        """
        doi = paper.clean_doi or paper.doi
        cache_key = doi or paper.clean_title

        # 1. Check persistent cache
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached:
                paper.scopus_indexed = cached.get("scopus")
                paper.wos_indexed = cached.get("wos")
                paper.ieee_indexed = cached.get("ieee")
                paper.open_access = cached.get("open_access", paper.open_access)
                paper.verification_source = cached.get("source", "Cache")
                return paper

        sources_used = []

        # =====================================================================
        # BRANCH 1: INSTITUTIONAL CREDENTIALS ACTIVE
        # =====================================================================
        if self.inst_token_flag:
            # A. Elsevier Scopus
            if not self.scopus_cb.is_tripped() and cfg.has_scopus_credentials:
                res = self.scopus_verifier.verify_doi(doi) if doi else self.scopus_verifier.verify_title(paper.title)
                if res is not None:
                    paper.scopus_indexed = res
                    sources_used.append("Scopus API")

            # B. Web of Science
            if not self.wos_cb.is_tripped() and cfg.WOS_API_KEY and doi:
                res = self.wos_verifier.verify_doi(doi)
                if res is not None:
                    paper.wos_indexed = res
                    sources_used.append("WoS API")

            # C. IEEE Xplore
            if not self.ieee_cb.is_tripped() and cfg.IEEE_API_KEY and doi:
                res = self.ieee_verifier.verify_doi(doi)
                if res is not None:
                    paper.ieee_indexed = res
                    sources_used.append("IEEE API")

        # Heuristic IEEE check
        if paper.ieee_indexed is None:
            if self.ieee_verifier.is_ieee_venue(paper.venue, doi):
                paper.ieee_indexed = True

        # =====================================================================
        # BRANCH 2: OPEN ACCESS / OPENALEX / LOCAL DB FALLBACK
        # =====================================================================
        # If Scopus or WoS remain unverified due to lack of token or tripped circuit
        if paper.scopus_indexed is None or paper.wos_indexed is None:
            # 1. Local ISSN hash check if paper has ISSNs
            if paper.issn_list:
                if paper.scopus_indexed is None:
                    local_scopus = self.local_db.is_scopus_issn(paper.issn_list)
                    if local_scopus is not None:
                        paper.scopus_indexed = local_scopus
                        sources_used.append("Local Scopus DB")

                if paper.wos_indexed is None:
                    local_wos = self.local_db.is_wos_issn(paper.issn_list)
                    if local_wos is not None:
                        paper.wos_indexed = local_wos
                        sources_used.append("Local WoS DB")

            # 2. Query OpenAlex CC0 registry if DOI available
            if doi and (paper.scopus_indexed is None or paper.wos_indexed is None or paper.open_access is None):
                oa_info = self.openalex_verifier.check_work(doi)
                if oa_info:
                    if paper.scopus_indexed is None:
                        paper.scopus_indexed = oa_info.get("is_scopus_indexed")
                        sources_used.append("OpenAlex CC0")
                    if paper.wos_indexed is None:
                        paper.wos_indexed = oa_info.get("is_wos_indexed")
                        if oa_info.get("is_wos_indexed"):
                            sources_used.append("OpenAlex/Local WoS")
                    if paper.open_access is None:
                        paper.open_access = oa_info.get("is_oa")
                    if not paper.pdf_link and oa_info.get("oa_url"):
                        paper.pdf_link = oa_info.get("oa_url")
                    if not paper.venue and oa_info.get("journal"):
                        paper.venue = oa_info.get("journal")

        # Fallback defaults if still unresolved
        if paper.scopus_indexed is None:
            paper.scopus_indexed = False
        if paper.wos_indexed is None:
            paper.wos_indexed = False
        if paper.ieee_indexed is None:
            paper.ieee_indexed = False
        if paper.open_access is None:
            paper.open_access = bool(paper.pdf_link or "open access" in paper.access_type.lower())

        paper.verification_source = ", ".join(sources_used) if sources_used else "Open Access Fallback"

        # Save to persistent cache
        if cache_key:
            self.cache.set(cache_key, {
                "scopus": paper.scopus_indexed,
                "wos": paper.wos_indexed,
                "ieee": paper.ieee_indexed,
                "open_access": paper.open_access,
                "source": paper.verification_source
            })

        return paper

    def verify_batch(self, papers: List[Paper], progress_callback: Optional[Any] = None) -> List[Paper]:
        """Verifies a list of candidate papers sequentially with pacing."""
        verified = []
        for idx, p in enumerate(papers, 1):
            v_p = self.verify_paper(p)
            verified.append(v_p)
            if progress_callback:
                progress_callback(idx, len(papers))

        self.cache.save()
        return verified
