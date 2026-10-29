"""
tests/test_verifier.py - Tests for CircuitBreaker, LocalDBMatcher, DualBranchVerifier,
multi-source academic verification, token pooling, and strict vs broad indexing filters.
"""

import unittest
from unittest.mock import patch, MagicMock

from verifier.circuit_breaker import CircuitBreaker
from verifier.local_db import LocalDBMatcher
from verifier.cache import VerificationCache
from verifier.dual_branch import DualBranchVerifier
from verifier.scopus import ScopusVerifier
from verifier.wos import WebOfScienceVerifier
from verifier.crossref_verifier import CrossrefVerifier
from verifier.arxiv_verifier import ArxivVerifier
from harvester.models import Paper


class TestCircuitBreaker(unittest.TestCase):
    def test_immediate_trip_on_401_403_429(self):
        cb = CircuitBreaker("TestService")
        self.assertFalse(cb.is_tripped())

        # Trip on 401 Unauthorized / Invalid Token
        cb.record_failure(status_code=401, error_message="Invalid institutional token")
        self.assertTrue(cb.is_tripped())
        self.assertIn("Authentication Error", cb.status_summary)

        # Reset
        cb.record_success()
        self.assertFalse(cb.is_tripped())

        # Trip on 429 Quota Exceeded
        cb.record_failure(status_code=429, error_message="Rate limit reached")
        self.assertTrue(cb.is_tripped())
        self.assertIn("Quota Exceeded", cb.status_summary)

    def test_consecutive_failure_threshold(self):
        cb = CircuitBreaker("TestService", failure_threshold=2)
        cb.record_failure(status_code=500, error_message="Internal Server Error")
        self.assertFalse(cb.is_tripped())
        cb.record_failure(status_code=500, error_message="Internal Server Error")
        self.assertTrue(cb.is_tripped())


class TestLocalDBMatcher(unittest.TestCase):
    def test_clean_issn(self):
        self.assertEqual(LocalDBMatcher.clean_issn("1016-0114"), "10160114")
        self.assertEqual(LocalDBMatcher.clean_issn("10160114"), "10160114")

    def test_issn_matching_with_mock_data(self):
        matcher = LocalDBMatcher()
        matcher.scopus_issns = {"10160114", "15684946"}
        matcher.wos_issns = {"10160114"}

        self.assertTrue(matcher.is_scopus_issn(["1016-0114"]))
        self.assertTrue(matcher.is_wos_issn(["1016-0114"]))
        self.assertFalse(matcher.is_wos_issn(["1568-4946"]))
        self.assertFalse(matcher.is_scopus_issn(["0000-0000"]))


class TestTokenPooling(unittest.TestCase):
    def test_scopus_key_rotation(self):
        cb = CircuitBreaker("ScopusTest")
        verifier = ScopusVerifier(cb)
        verifier.key_pool = ["KEY_ALPHA", "KEY_BETA", "KEY_GAMMA"]
        verifier.current_key_idx = 0

        self.assertEqual(verifier._get_api_key(), "KEY_ALPHA")
        verifier._rotate_key()
        self.assertEqual(verifier._get_api_key(), "KEY_BETA")
        verifier._rotate_key()
        self.assertEqual(verifier._get_api_key(), "KEY_GAMMA")
        verifier._rotate_key()
        self.assertEqual(verifier._get_api_key(), "KEY_ALPHA")

    def test_wos_key_rotation(self):
        cb = CircuitBreaker("WoSTest")
        verifier = WebOfScienceVerifier(cb)
        verifier.key_pool = ["WOS_KEY_1", "WOS_KEY_2"]
        verifier.current_key_idx = 0

        self.assertEqual(verifier._get_api_key(), "WOS_KEY_1")
        verifier._rotate_key()
        self.assertEqual(verifier._get_api_key(), "WOS_KEY_2")


class TestMultiSourceVerificationAndFilters(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory verification cache for isolated testing
        self.cache = VerificationCache(cache_path="cache/test_verifier_cache.json")
        self.local_db = LocalDBMatcher()
        self.local_db.scopus_issns = {"10160114"}
        self.local_db.wos_issns = {"10160114"}

    def test_consolidated_verified_sources_column(self):
        verifier = DualBranchVerifier(local_db=self.local_db, cache=self.cache, inst_token_flag=False)

        # Mock OpenAlex, Crossref, and arXiv responses
        verifier.openalex_verifier.check_work = MagicMock(return_value={
            "found": True,
            "is_scopus_indexed": True,
            "is_wos_indexed": False,
            "journal": "Fuzzy Sets and Systems",
            "is_oa": True,
            "oa_url": "https://example.org/oa.pdf"
        })
        verifier.crossref_verifier.verify_doi = MagicMock(return_value={
            "confirmed": True,
            "title": "A Study of Fuzzy Sets",
            "venue": "Fuzzy Sets and Systems",
            "is_peer_reviewed": True,
            "doi": "10.1016/j.fss.2020.01"
        })
        verifier.arxiv_verifier.verify_paper = MagicMock(return_value={
            "confirmed": True,
            "is_preprint": True,
            "pdf_link": "https://arxiv.org/pdf/2001.0001.pdf"
        })

        p = Paper(
            title="A Study of Fuzzy Sets",
            doi="10.1016/j.fss.2020.01",
            venue="Fuzzy Sets and Systems"
        )

        verified = verifier.verify_paper(p)

        # Verify multi-source consolidation
        self.assertIn("Scopus", verified.verified_sources)
        self.assertIn("Crossref", verified.verified_sources)
        self.assertIn("OpenAlex", verified.verified_sources)
        self.assertIn("arXiv", verified.verified_sources)
        self.assertTrue(verified.scopus_indexed)
        self.assertTrue(verified.open_access)
        self.assertEqual(verified.pdf_link, "https://example.org/oa.pdf")

    def test_strict_vs_broad_indexing_filtering(self):
        verifier = DualBranchVerifier(local_db=self.local_db, cache=self.cache, inst_token_flag=False)

        p1_indexed = Paper(title="Indexed Scopus Paper", doi="10.1/scopus")
        p1_indexed.scopus_indexed = True
        p1_indexed.wos_indexed = False

        p2_indexed = Paper(title="Indexed WoS Paper", doi="10.1/wos")
        p2_indexed.scopus_indexed = False
        p2_indexed.wos_indexed = True

        p3_non_indexed = Paper(title="Preprint arXiv Only", doi="10.1/arxiv")
        p3_non_indexed.scopus_indexed = False
        p3_non_indexed.wos_indexed = False

        papers = [p1_indexed, p2_indexed, p3_non_indexed]

        # 1. Strict filtering enabled: only p1 and p2 should be retained
        retained, excluded_count = verifier.filter_indexed_papers(papers)
        self.assertEqual(len(retained), 2)
        self.assertEqual(excluded_count, 1)
        self.assertIn(p1_indexed, retained)
        self.assertIn(p2_indexed, retained)
        self.assertNotIn(p3_non_indexed, retained)

    def test_fallback_routing_when_tokens_missing(self):
        verifier = DualBranchVerifier(local_db=self.local_db, cache=self.cache, inst_token_flag=False)

        # Mock OpenAlex return to prevent hanging network calls in sandboxed test
        verifier.openalex_verifier.check_work = MagicMock(return_value={
            "found": True,
            "is_scopus_indexed": False,
            "is_wos_indexed": False,
            "is_oa": True,
            "oa_url": "https://ieeexplore.ieee.org/sample.pdf",
            "journal": "IEEE Computational Intelligence Magazine"
        })
        verifier.crossref_verifier.verify_doi = MagicMock(return_value={
            "confirmed": True,
            "venue": "IEEE Computational Intelligence Magazine",
            "is_peer_reviewed": True
        })

        p = Paper(
            title="Fuzzy Sets in Data Analysis",
            venue="IEEE Computational Intelligence Magazine",
            doi="10.1109/MCI.2018.2881642"
        )
        verified = verifier.verify_paper(p)
        self.assertIsNotNone(verified.scopus_indexed)
        self.assertIsNotNone(verified.wos_indexed)
        self.assertTrue(verified.ieee_indexed)  # heuristic IEEE check
        self.assertIsNotNone(verified.verification_source)
        self.assertTrue(len(verified.verified_sources) > 0)


if __name__ == "__main__":
    unittest.main()
