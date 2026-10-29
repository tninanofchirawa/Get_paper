"""
verifier/tiered_verifier.py - Three-way workload partitioning and tiered verification engine.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.

Architecture:
1. Deduplicated unified queue: candidate papers are partitioned into three equal, disjoint shards:
   - Shard A -> Semantic Scholar (Dedicated worker, strict 1.05s sequential delay, x-api-key)
   - Shard B -> OpenAlex (Works API, polite email User-Agent, 10 req/s)
   - Shard C -> Crossref (REST API, DOI/bibliographic match, polite pool)
2. Dynamic sequential fallback routing:
   - Round 1: Partitioned execution across Shard A, B, C.
   - Round 2: Ring re-routing of unmatched/error records:
       Shard A failures -> OpenAlex
       Shard B failures -> Crossref
       Shard C failures -> Semantic Scholar
   - Round 3: Final catch-all across 3rd provider ring, arXiv, and DOAJ.
3. Semantic Scholar Safety Valve:
   - If Semantic Scholar issues a 429, immediately pause queries to that endpoint for 5–6s,
     shift all remaining Shard A work into OpenAlex and Crossref queues, and resume only when cooldown expires.
4. Output Tracking:
   - Explicitly tags resolving provider in 'Verified_Via' column:
     (OpenAlex, Crossref, Semantic_Scholar, arXiv, DOAJ, or Unverified).
"""

import time
import json
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple, Set
import concurrent.futures

from config import cfg
from harvester.models import Paper, sanitize_doi, clean_matching_title
from verifier.circuit_breaker import CircuitBreaker
from verifier.local_matcher import LocalDBMatcher
from verifier.cache import VerificationCache
from verifier.semantic_scholar_verifier import SemanticScholarVerifier
from verifier.openalex_verifier import OpenAlexVerifier
from verifier.crossref_verifier import CrossrefVerifier
from verifier.arxiv_verifier import ArxivVerifier
from verifier.doaj_verifier import DoajVerifier

logger = logging.getLogger("TieredVerifier")


class SemanticScholarSafetyValve:
    """
    Safety valve for Semantic Scholar:
    When HTTP 429 is encountered, pauses endpoint queries for 5–6 seconds (default: 5.5s),
    shifts remaining Shard A work into OpenAlex and Crossref queues,
    and resumes queries only when cooldown expires.
    """

    def __init__(self, cooldown_seconds: float = 5.5):
        self.cooldown_seconds = cooldown_seconds
        self.cooldown_until = 0.0
        self.lock = threading.Lock()
        self.total_trips = 0

    def trip(self):
        with self.lock:
            self.total_trips += 1
            self.cooldown_until = time.monotonic() + self.cooldown_seconds
            logger.warning(
                f"⚠️ [Semantic Scholar Safety Valve] HTTP 429 Rate Limit Hit (Trip #{self.total_trips})! "
                f"Pausing Semantic Scholar for {self.cooldown_seconds:.1f}s and re-routing queue."
            )
            print(
                f"⚠️ [Semantic Scholar Safety Valve] HTTP 429 Hit. "
                f"Pausing S2 endpoint for {self.cooldown_seconds:.1f}s. Shifting queue to OpenAlex & Crossref."
            )

    @property
    def is_paused(self) -> bool:
        with self.lock:
            return time.monotonic() < self.cooldown_until

    def remaining_cooldown(self) -> float:
        with self.lock:
            return max(0.0, self.cooldown_until - time.monotonic())

    def wait_if_needed(self):
        rem = self.remaining_cooldown()
        if rem > 0:
            logger.info(f"[SemanticScholarSafetyValve] Waiting {rem:.2f}s for S2 cooldown to expire...")
            time.sleep(rem)


class TieredWorkloadVerifier:
    """
    Unified academic aggregator verification coordinator with 3-way workload partitioning,
    strict sequential pacing, and 3-round tiered fallback routing.
    """

    def __init__(
        self,
        semantic_scholar_verifier: Optional[SemanticScholarVerifier] = None,
        openalex_verifier: Optional[OpenAlexVerifier] = None,
        crossref_verifier: Optional[CrossrefVerifier] = None,
        arxiv_verifier: Optional[ArxivVerifier] = None,
        doaj_verifier: Optional[DoajVerifier] = None,
        local_db: Optional[LocalDBMatcher] = None,
        cache: Optional[VerificationCache] = None,
        s2_cooldown_seconds: float = 5.5,
        s2_delay_seconds: float = 1.05
    ):
        self.local_db = local_db or LocalDBMatcher()
        self.cache = cache or VerificationCache()

        # Circuit breakers
        self.s2_cb = CircuitBreaker("Semantic Scholar", failure_threshold=3)
        self.openalex_cb = CircuitBreaker("OpenAlex", failure_threshold=3)
        self.crossref_cb = CircuitBreaker("Crossref", failure_threshold=3)
        self.arxiv_cb = CircuitBreaker("arXiv", failure_threshold=3)
        self.doaj_cb = CircuitBreaker("DOAJ", failure_threshold=3)

        # Provider verifier clients
        self.s2_verifier = semantic_scholar_verifier or SemanticScholarVerifier(self.s2_cb)
        self.openalex_verifier = openalex_verifier or OpenAlexVerifier(self.local_db)
        self.crossref_verifier = crossref_verifier or CrossrefVerifier(self.crossref_cb)
        self.arxiv_verifier = arxiv_verifier or ArxivVerifier(self.arxiv_cb)
        self.doaj_verifier = doaj_verifier or DoajVerifier(self.doaj_cb)

        # Safety valve & pacing
        self.safety_valve = SemanticScholarSafetyValve(cooldown_seconds=s2_cooldown_seconds)
        self.s2_delay_seconds = s2_delay_seconds

        # Wire safety valve callback into S2 client if available
        if hasattr(self.s2_verifier, "client") and hasattr(self.s2_verifier.client, "on_429_callback"):
            self.s2_verifier.client.on_429_callback = self.safety_valve.trip

    @staticmethod
    def partition_candidates(papers: List[Paper]) -> Tuple[List[Paper], List[Paper], List[Paper]]:
        """
        Partitions an initial batch of N candidate papers into three equal, disjoint shards:
        Shard A (N/3) -> Semantic Scholar
        Shard B (N/3) -> OpenAlex
        Shard C (N/3) -> Crossref
        """
        shard_a: List[Paper] = []
        shard_b: List[Paper] = []
        shard_c: List[Paper] = []

        for idx, paper in enumerate(papers):
            mod = idx % 3
            if mod == 0:
                shard_a.append(paper)
            elif mod == 1:
                shard_b.append(paper)
            else:
                shard_c.append(paper)

        return shard_a, shard_b, shard_c

    def _verify_with_semantic_scholar(self, paper: Paper) -> Tuple[bool, Optional[Dict[str, Any]], bool]:
        """
        Queries Semantic Scholar with strict 1.05s sequential delay.
        Returns: (is_success, data_dict, is_429)
        """
        if self.safety_valve.is_paused:
            return False, None, True

        doi = paper.clean_doi or paper.doi
        # Strict sequential delay to respect 1 req/sec cap
        time.sleep(self.s2_delay_seconds)

        try:
            res = None
            if doi:
                res = self.s2_verifier.verify_doi(doi)
            elif paper.title and hasattr(self.s2_verifier, "verify_title"):
                res = self.s2_verifier.verify_title(paper.title)

            # Check if 429 was encountered
            client = getattr(self.s2_verifier, "client", None)
            if client and getattr(client, "last_status_code", None) == 429:
                self.safety_valve.trip()
                return False, None, True

            if res and (res.get("confirmed") or res.get("title")):
                return True, res, False

            return False, None, False
        except Exception as e:
            logger.debug(f"[S2Worker] Error querying '{doi or paper.title}': {e}")
            return False, None, False

    def _verify_with_openalex(self, paper: Paper) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Queries OpenAlex Works API (configured with polite User-Agent pool email header)."""
        doi = paper.clean_doi or paper.doi
        try:
            res = None
            if doi:
                if hasattr(self.openalex_verifier, "verify_doi"):
                    res = self.openalex_verifier.verify_doi(doi)
                elif hasattr(self.openalex_verifier, "check_work"):
                    chk = self.openalex_verifier.check_work(doi)
                    if chk and chk.get("found"):
                        res = {
                            "confirmed": True,
                            "venue": chk.get("journal", ""),
                            "issn_list": chk.get("issns", []),
                            "is_oa": chk.get("is_oa", False),
                            "pdf_link": chk.get("oa_url", ""),
                            "is_scopus_indexed": chk.get("is_scopus_indexed", False),
                            "is_wos_indexed": chk.get("is_wos_indexed", False),
                            "doi": doi
                        }
            elif paper.title and hasattr(self.openalex_verifier, "verify_title"):
                res = self.openalex_verifier.verify_title(paper.title)

            if res and (res.get("confirmed") or res.get("found")):
                return True, res
            return False, None
        except Exception as e:
            logger.debug(f"[OpenAlexWorker] Error querying '{doi or paper.title}': {e}")
            return False, None

    def _verify_with_crossref(self, paper: Paper) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Queries Crossref REST API via DOI or bibliographic match."""
        doi = paper.clean_doi or paper.doi
        try:
            res = None
            if doi:
                res = self.crossref_verifier.verify_doi(doi)
            elif paper.title and hasattr(self.crossref_verifier, "verify_title"):
                res = self.crossref_verifier.verify_title(paper.title)

            if res and (res.get("confirmed") or res.get("title")):
                return True, res
            return False, None
        except Exception as e:
            logger.debug(f"[CrossrefWorker] Error querying '{doi or paper.title}': {e}")
            return False, None

    def _verify_with_arxiv(self, paper: Paper) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Queries arXiv preprint registry."""
        doi = paper.clean_doi or paper.doi
        try:
            res = self.arxiv_verifier.verify_paper(title=paper.title, doi=doi)
            if res and res.get("confirmed"):
                return True, res
            return False, None
        except Exception as e:
            logger.debug(f"[ArxivWorker] Error querying '{paper.title}': {e}")
            return False, None

    def _verify_with_doaj(self, paper: Paper) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Queries DOAJ open access journal registry."""
        doi = paper.clean_doi or paper.doi
        try:
            res = None
            if doi and hasattr(self.doaj_verifier, "verify_doi"):
                res = self.doaj_verifier.verify_doi(doi)
            elif paper.title and hasattr(self.doaj_verifier, "verify_title"):
                res = self.doaj_verifier.verify_title(paper.title)

            if res and res.get("confirmed"):
                return True, res
            return False, None
        except Exception as e:
            logger.debug(f"[DoajWorker] Error querying '{paper.title}': {e}")
            return False, None

    def _apply_verification(self, paper: Paper, provider: str, data: Dict[str, Any]):
        """Updates paper record with resolving provider tag and enriched metadata."""
        paper.verified_via = provider

        # Add to verified sources list
        source_label = provider.replace("_", " ")
        if source_label not in paper.verified_sources:
            paper.verified_sources.append(source_label)

        if not paper.verification_source:
            paper.verification_source = source_label
        else:
            sources = [s.strip() for s in paper.verification_source.split(",") if s.strip()]
            if source_label not in sources:
                sources.append(source_label)
                paper.verification_source = ", ".join(sources)

        # Venue and DOI enrichment
        if not paper.venue and data.get("venue"):
            paper.venue = data["venue"]
        if not paper.doi and data.get("doi"):
            paper.doi = sanitize_doi(data["doi"])
            paper.clean_doi = paper.doi
            if not paper.url:
                paper.url = f"https://doi.org/{paper.clean_doi}"

        # PDF Link and Open Access flags
        pdf = data.get("pdf_link") or data.get("oa_url") or ""
        if not paper.pdf_link and pdf:
            paper.pdf_link = pdf
        if pdf or data.get("is_oa"):
            paper.open_access = True

        # ISSN matching against offline Scopus and Web of Science lists
        issns = data.get("issn_list") or data.get("issns") or []
        if issns:
            paper.issn_list = list(set(paper.issn_list + issns))
            if self.local_db.is_scopus_issn(issns):
                paper.scopus_indexed = True
                if "Scopus" not in paper.verified_sources:
                    paper.verified_sources.append("Scopus")
            if self.local_db.is_wos_issn(issns):
                paper.wos_indexed = True
                if "Web of Science" not in paper.verified_sources:
                    paper.verified_sources.append("Web of Science")

        if data.get("is_scopus_indexed"):
            paper.scopus_indexed = True
            if "Scopus" not in paper.verified_sources:
                paper.verified_sources.append("Scopus")
        if data.get("is_wos_indexed"):
            paper.wos_indexed = True
            if "Web of Science" not in paper.verified_sources:
                paper.verified_sources.append("Web of Science")

        # Default booleans
        if paper.scopus_indexed is None:
            paper.scopus_indexed = False
        if paper.wos_indexed is None:
            paper.wos_indexed = False
        if paper.ieee_indexed is None:
            paper.ieee_indexed = False
        if paper.open_access is None:
            paper.open_access = bool(paper.pdf_link or "open access" in paper.access_type.lower())

        # Save in persistent verification cache
        cache_key = paper.clean_doi or paper.clean_title
        if cache_key:
            self.cache.set(cache_key, {
                "doi": paper.clean_doi or paper.doi,
                "title": paper.title,
                "venue": paper.venue,
                "scopus": paper.scopus_indexed,
                "wos": paper.wos_indexed,
                "ieee": paper.ieee_indexed,
                "open_access": paper.open_access,
                "source": paper.verification_source,
                "verified_sources": paper.verified_sources,
                "verified_via": paper.verified_via
            })

    def verify_batch(
        self,
        papers: List[Paper],
        progress_callback: Optional[Any] = None
    ) -> List[Paper]:
        """
        Executes unified 3-way workload partitioning with multi-round sequential fallback:
          - Pre-check: Persistent Cache & Local DB (O(1) resolution)
          - Round 1 (Partitioned Execution):
              Shard A -> Semantic Scholar (Sequential, 1.05s delay)
              Shard B -> OpenAlex
              Shard C -> Crossref
          - Round 2 (Ring Fallback Re-routing):
              Shard A failures -> OpenAlex
              Shard B failures -> Crossref
              Shard C failures -> Semantic Scholar
          - Round 3 (Final Open Access Catch-All):
              3rd provider in ring, followed by arXiv and DOAJ
        """
        if not papers:
            return []

        # Deduplicate papers into a unified queue map by DOI or clean title
        unified_candidates: List[Paper] = []
        seen_keys: Set[str] = set()

        for p in papers:
            key = p.clean_doi or p.clean_title or p.title
            if key and key not in seen_keys:
                seen_keys.add(key)
                unified_candidates.append(p)
            elif not key:
                unified_candidates.append(p)

        unresolved: List[Paper] = []

        # Step 0: Pre-Check against Cache and Local Offline DB
        for p in unified_candidates:
            cache_key = p.clean_doi or p.clean_title
            cached = self.cache.get(cache_key) if cache_key else None
            if cached:
                p.scopus_indexed = cached.get("scopus", False)
                p.wos_indexed = cached.get("wos", False)
                p.ieee_indexed = cached.get("ieee", False)
                p.open_access = cached.get("open_access", p.open_access)
                p.verification_source = cached.get("source", "Cache")
                p.verified_sources = cached.get("verified_sources", [])
                p.verified_via = cached.get("verified_via", "Cache")
                continue

            # Local offline DB check
            if p.issn_list:
                if self.local_db.is_scopus_issn(p.issn_list):
                    p.scopus_indexed = True
                    p.verified_sources.append("Scopus")
                if self.local_db.is_wos_issn(p.issn_list):
                    p.wos_indexed = True
                    p.verified_sources.append("Web of Science")

            unresolved.append(p)

        if not unresolved:
            return unified_candidates

        # Step 1: Three-Way Workload Partitioning (Divide by 3)
        shard_a, shard_b, shard_c = self.partition_candidates(unresolved)
        logger.info(
            f"[WorkloadPartition] Total: {len(unresolved)} candidates partitioned into: "
            f"Shard A (Semantic Scholar): {len(shard_a)} | "
            f"Shard B (OpenAlex): {len(shard_b)} | "
            f"Shard C (Crossref): {len(shard_c)}"
        )
        print(
            f"⚡ [Workload Partitioning] Distributed {len(unresolved)} candidates: "
            f"Shard A (Semantic Scholar): {len(shard_a)} | "
            f"Shard B (OpenAlex): {len(shard_b)} | "
            f"Shard C (Crossref): {len(shard_c)}"
        )

        round_2_queue: List[Tuple[Paper, str]] = []  # (paper, initial_shard)

        # Step 2: Round 1 Execution
        # Shard A Worker (Semantic Scholar) with 429 Safety Valve queue-shift
        def run_shard_a(papers_a: List[Paper]):
            nonlocal round_2_queue
            shifted_to_b: List[Paper] = []
            shifted_to_c: List[Paper] = []

            for idx, p in enumerate(papers_a):
                if self.safety_valve.is_paused:
                    # Semantic Scholar safety valve tripped: shift all remaining Shard A work
                    rem_papers = papers_a[idx:]
                    for s_idx, rem_p in enumerate(rem_papers):
                        if s_idx % 2 == 0:
                            shifted_to_b.append(rem_p)
                        else:
                            shifted_to_c.append(rem_p)
                    logger.info(
                        f"[SafetyValve Active] Shifted {len(rem_papers)} Shard A candidates: "
                        f"{len(shifted_to_b)} -> OpenAlex, {len(shifted_to_c)} -> Crossref."
                    )
                    break

                success, data, is_429 = self._verify_with_semantic_scholar(p)
                if is_429:
                    # Trip safety valve and shift subsequent papers
                    self.safety_valve.trip()
                    rem_papers = papers_a[idx + 1:]
                    for s_idx, rem_p in enumerate(rem_papers):
                        if s_idx % 2 == 0:
                            shifted_to_b.append(rem_p)
                        else:
                            shifted_to_c.append(rem_p)
                    # Current 429 paper goes to Round 2 fallback
                    round_2_queue.append((p, "A"))
                    break
                elif success and data:
                    self._apply_verification(p, "Semantic_Scholar", data)
                else:
                    round_2_queue.append((p, "A"))

            return shifted_to_b, shifted_to_c

        # Execute Shard B Worker (OpenAlex)
        def run_shard_b(papers_b: List[Paper]) -> List[Tuple[Paper, str]]:
            unmatched = []
            for p in papers_b:
                success, data = self._verify_with_openalex(p)
                if success and data:
                    self._apply_verification(p, "OpenAlex", data)
                else:
                    unmatched.append((p, "B"))
            return unmatched

        # Execute Shard C Worker (Crossref)
        def run_shard_c(papers_c: List[Paper]) -> List[Tuple[Paper, str]]:
            unmatched = []
            for p in papers_c:
                success, data = self._verify_with_crossref(p)
                if success and data:
                    self._apply_verification(p, "Crossref", data)
                else:
                    unmatched.append((p, "C"))
            return unmatched

        # Run Shards independently in parallel thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            fut_a = executor.submit(run_shard_a, shard_a)
            fut_b = executor.submit(run_shard_b, shard_b)
            fut_c = executor.submit(run_shard_c, shard_c)

            shifted_b, shifted_c = fut_a.result()
            unmatched_b = fut_b.result()
            unmatched_c = fut_c.result()

            round_2_queue.extend(unmatched_b)
            round_2_queue.extend(unmatched_c)

        # Process any papers shifted out of Shard A due to safety valve trip
        if shifted_b or shifted_c:
            print(f"🔄 [Safety Valve Shift] Executing {len(shifted_b)} shifted on OpenAlex, {len(shifted_c)} on Crossref...")
            if shifted_b:
                for p in shifted_b:
                    success, data = self._verify_with_openalex(p)
                    if success and data:
                        self._apply_verification(p, "OpenAlex", data)
                    else:
                        round_2_queue.append((p, "B"))
            if shifted_c:
                for p in shifted_c:
                    success, data = self._verify_with_crossref(p)
                    if success and data:
                        self._apply_verification(p, "Crossref", data)
                    else:
                        round_2_queue.append((p, "C"))

        logger.info(f"[Round 1 Finished] {len(round_2_queue)} candidate papers forwarded to Round 2 Fallback Queue.")

        # Step 3: Round 2 (Dynamic Sequential Fallback Routing / Re-routing)
        # Ring rotation:
        # Shard A failures -> OpenAlex
        # Shard B failures -> Crossref
        # Shard C failures -> Semantic Scholar
        round_3_queue: List[Tuple[Paper, str]] = []

        for paper, initial_shard in round_2_queue:
            resolved = False
            if initial_shard == "A":
                # Route to OpenAlex
                success, data = self._verify_with_openalex(paper)
                if success and data:
                    self._apply_verification(paper, "OpenAlex", data)
                    resolved = True
            elif initial_shard == "B":
                # Route to Crossref
                success, data = self._verify_with_crossref(paper)
                if success and data:
                    self._apply_verification(paper, "Crossref", data)
                    resolved = True
            elif initial_shard == "C":
                # Route to Semantic Scholar (respect safety valve cooldown)
                if self.safety_valve.is_paused:
                    self.safety_valve.wait_if_needed()
                success, data, _ = self._verify_with_semantic_scholar(paper)
                if success and data:
                    self._apply_verification(paper, "Semantic_Scholar", data)
                    resolved = True

            if not resolved:
                round_3_queue.append((paper, initial_shard))

        logger.info(f"[Round 2 Finished] {len(round_3_queue)} candidate papers forwarded to Round 3 Catch-All Queue.")

        # Step 4: Round 3 (Final Open Access Catch-All)
        # 3rd provider ring check, followed by arXiv and DOAJ
        for paper, initial_shard in round_3_queue:
            resolved = False

            # 1. Check 3rd provider in ring
            if initial_shard == "A":
                # Checked S2, OpenAlex -> Check Crossref
                success, data = self._verify_with_crossref(paper)
                if success and data:
                    self._apply_verification(paper, "Crossref", data)
                    resolved = True
            elif initial_shard == "B":
                # Checked OpenAlex, Crossref -> Check Semantic Scholar
                if not self.safety_valve.is_paused:
                    success, data, _ = self._verify_with_semantic_scholar(paper)
                    if success and data:
                        self._apply_verification(paper, "Semantic_Scholar", data)
                        resolved = True
            elif initial_shard == "C":
                # Checked Crossref, S2 -> Check OpenAlex
                success, data = self._verify_with_openalex(paper)
                if success and data:
                    self._apply_verification(paper, "OpenAlex", data)
                    resolved = True

            # 2. arXiv Preprints Catch-All
            if not resolved:
                success, data = self._verify_with_arxiv(paper)
                if success and data:
                    self._apply_verification(paper, "arXiv", data)
                    if not paper.venue:
                        paper.publication_type = "Preprint"
                    resolved = True

            # 3. DOAJ Open Access Catch-All
            if not resolved:
                success, data = self._verify_with_doaj(paper)
                if success and data:
                    self._apply_verification(paper, "DOAJ", data)
                    resolved = True

            # 4. Final Unverified / Non-Indexed flag
            if not resolved:
                paper.verified_via = "Unverified"
                if paper.scopus_indexed is None:
                    paper.scopus_indexed = False
                if paper.wos_indexed is None:
                    paper.wos_indexed = False
                if paper.ieee_indexed is None:
                    paper.ieee_indexed = False
                if paper.open_access is None:
                    paper.open_access = False
                if not paper.index_status:
                    paper.index_status = "Non-Indexed"

        # Final cache persistence
        self.cache.save()

        return unified_candidates
