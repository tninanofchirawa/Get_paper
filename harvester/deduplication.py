"""
harvester/deduplication.py - Candidate-bucketed fuzzy deduplicator with exact DOI matching.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging
from difflib import SequenceMatcher
from collections import defaultdict
from typing import List, Set, Dict, Tuple

from harvester.models import Paper

logger = logging.getLogger("DeduplicationEngine")


class DeduplicationEngine:
    """
    Dual-layer candidate-bucketed deduplication:
    1. Exact canonical DOI hashing (O(1)).
    2. Inverted token indexing + fast SequenceMatcher (>= 0.90) for title similarity.
    """

    def __init__(self, similarity_threshold: float = 0.90):
        self.threshold = similarity_threshold
        self.seen_dois: Set[str] = set()
        self.unique_papers: List[Paper] = []
        self.token_buckets: Dict[str, List[int]] = defaultdict(list)

        # Metric counters
        self.raw_scraped_count: int = 0
        self.duplicates_removed_count: int = 0

    @staticmethod
    def _extract_tokens(clean_title: str) -> Set[str]:
        """Extracts significant tokens of length >= 4 for bucket indexing."""
        return {w for w in clean_title.split() if len(w) >= 4}

    def _is_fuzzy_duplicate(self, candidate_clean_title: str) -> bool:
        """Checks if candidate title matches any already accepted paper above threshold."""
        tokens = self._extract_tokens(candidate_clean_title)
        candidate_indices: Set[int] = set()

        for t in tokens:
            for idx in self.token_buckets.get(t, []):
                candidate_indices.add(idx)

        # Compare only against candidates that share at least one keyword token
        for idx in candidate_indices:
            existing_title = self.unique_papers[idx].clean_title
            ratio = SequenceMatcher(None, candidate_clean_title, existing_title).ratio()
            if ratio >= self.threshold:
                return True

        return False

    def add_paper(self, paper: Paper) -> bool:
        """
        Attempts to add paper.
        Returns True if paper is unique and accepted, False if duplicate.
        """
        self.raw_scraped_count += 1

        # 1. Exact DOI match
        if paper.clean_doi:
            if paper.clean_doi in self.seen_dois:
                self.duplicates_removed_count += 1
                return False

        # 2. Fuzzy Title match
        if not paper.clean_title:
            self.duplicates_removed_count += 1
            return False

        if self._is_fuzzy_duplicate(paper.clean_title):
            self.duplicates_removed_count += 1
            return False

        # Accept paper
        paper_idx = len(self.unique_papers)
        self.unique_papers.append(paper)

        if paper.clean_doi:
            self.seen_dois.add(paper.clean_doi)

        for token in self._extract_tokens(paper.clean_title):
            self.token_buckets[token].append(paper_idx)

        return True

    def add_papers(self, papers: List[Paper]) -> Tuple[int, int, int]:
        """
        Batch adds papers.
        Returns: (raw_added, duplicates_dropped, unique_retained)
        """
        initial_raw = self.raw_scraped_count
        initial_dups = self.duplicates_removed_count

        for p in papers:
            self.add_paper(p)

        added_raw = self.raw_scraped_count - initial_raw
        dropped_dups = self.duplicates_removed_count - initial_dups
        retained = len(self.unique_papers)

        logger.info(
            f"[Deduplication] Batch processed: raw_scraped={added_raw}, "
            f"duplicates_removed={dropped_dups}, unique_retained={retained}"
        )
        return added_raw, dropped_dups, retained

    @property
    def metrics(self) -> Dict[str, int]:
        """Returns standard metrics dict."""
        return {
            "raw_scraped": self.raw_scraped_count,
            "duplicates_removed": self.duplicates_removed_count,
            "unique_retained": len(self.unique_papers)
        }
