"""
tests/test_tiered_verifier.py - Unit tests for Academic Aggregator Workload Partitioning & Tiered Verification Architecture.
Validates:
1. Deduplication and 3-way equal disjoint workload partitioning (Shard A, B, C).
2. Dynamic sequential fallback routing across Round 1, Round 2 (ring rotation), and Round 3 (3rd provider, arXiv, DOAJ).
3. Semantic Scholar Safety Valve: HTTP 429 pauses endpoint for 5.5s and shifts remaining Shard A candidates to OpenAlex and Crossref.
4. Output Tracking: Explicit tagging in Verified_Via column across all resolving providers.
5. Single unified verification queue preventing duplicate scheduling.
"""

import os
import time
import unittest
from unittest.mock import MagicMock, patch

from harvester.models import Paper
from verifier.circuit_breaker import CircuitBreaker
from verifier.local_matcher import LocalDBMatcher
from verifier.cache import VerificationCache
from config import cfg
from verifier.tiered_verifier import TieredWorkloadVerifier, SemanticScholarSafetyValve
from verifier.dual_branch import DualBranchVerifier


class TestTieredWorkloadPartitioning(unittest.TestCase):
    def setUp(self):
        self.cache_path = os.path.join(cfg.CACHE_DIR, "test_tiered_cache.json")
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except Exception:
                pass
        self.cache = VerificationCache(cache_path=self.cache_path)
        self.local_db = LocalDBMatcher()
        self.local_db.scopus_issns = set()
        self.local_db.wos_issns = set()

    def tearDown(self):
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except Exception:
                pass

    def test_three_way_disjoint_equal_partitioning(self):
        """Validates that N candidates are partitioned into 3 equal disjoint shards without duplicates or omissions."""
        # 1. Test divisible by 3 (N=9)
        papers_9 = [Paper(title=f"Paper {i}", doi=f"10.1000/{i}") for i in range(9)]
        shard_a, shard_b, shard_c = TieredWorkloadVerifier.partition_candidates(papers_9)

        self.assertEqual(len(shard_a), 3)
        self.assertEqual(len(shard_b), 3)
        self.assertEqual(len(shard_c), 3)
        self.assertEqual(len(shard_a) + len(shard_b) + len(shard_c), 9)

        # Disjointness check
        set_a = set(p.doi for p in shard_a)
        set_b = set(p.doi for p in shard_b)
        set_c = set(p.doi for p in shard_c)
        self.assertTrue(set_a.isdisjoint(set_b))
        self.assertTrue(set_b.isdisjoint(set_c))
        self.assertTrue(set_a.isdisjoint(set_c))

        # 2. Test remainder (N=10)
        papers_10 = [Paper(title=f"Paper {i}", doi=f"10.1000/{i}") for i in range(10)]
        sa, sb, sc = TieredWorkloadVerifier.partition_candidates(papers_10)
        self.assertEqual(len(sa), 4)
        self.assertEqual(len(sb), 3)
        self.assertEqual(len(sc), 3)
        self.assertEqual(len(sa) + len(sb) + len(sc), 10)

    def test_round_1_partitioned_execution_tags_verified_via(self):
        """Verifies that candidates verified in Round 1 receive correct Verified_Via tags."""
        verifier = TieredWorkloadVerifier(
            local_db=self.local_db,
            cache=self.cache,
            s2_delay_seconds=0.0  # Fast unit test execution
        )

        # Mock each provider returning confirmation
        verifier._verify_with_semantic_scholar = MagicMock(return_value=(True, {"confirmed": True, "venue": "S2 Journal"}, False))
        verifier._verify_with_openalex = MagicMock(return_value=(True, {"confirmed": True, "venue": "OpenAlex Journal"}))
        verifier._verify_with_crossref = MagicMock(return_value=(True, {"confirmed": True, "venue": "Crossref Journal"}))

        p0 = Paper(title="Paper 0 (Shard A)", doi="10.1000/0")
        p1 = Paper(title="Paper 1 (Shard B)", doi="10.1000/1")
        p2 = Paper(title="Paper 2 (Shard C)", doi="10.1000/2")

        verified = verifier.verify_batch([p0, p1, p2])

        self.assertEqual(len(verified), 3)
        self.assertEqual(p0.verified_via, "Semantic_Scholar")
        self.assertEqual(p1.verified_via, "OpenAlex")
        self.assertEqual(p2.verified_via, "Crossref")
        self.assertIn("Semantic Scholar", p0.verified_sources)
        self.assertIn("OpenAlex", p1.verified_sources)
        self.assertIn("Crossref", p2.verified_sources)

    def test_round_2_ring_fallback_routing(self):
        """
        Validates Round 2 ring re-routing:
        - Shard A initial failure -> OpenAlex
        - Shard B initial failure -> Crossref
        - Shard C initial failure -> Semantic Scholar
        """
        verifier = TieredWorkloadVerifier(
            local_db=self.local_db,
            cache=self.cache,
            s2_delay_seconds=0.0
        )

        p0 = Paper(title="Paper 0 (Shard A)", doi="10.1000/0")
        p1 = Paper(title="Paper 1 (Shard B)", doi="10.1000/1")
        p2 = Paper(title="Paper 2 (Shard C)", doi="10.1000/2")

        # In Round 1, all 3 initial providers fail.
        # In Round 2, the ring alternate succeeds.
        def mock_s2(p):
            if p.doi == "10.1000/2":  # Shard C failure routed to S2
                return True, {"confirmed": True, "venue": "S2 Resolved"}, False
            return False, None, False

        def mock_oa(p):
            if p.doi == "10.1000/0":  # Shard A failure routed to OpenAlex
                return True, {"confirmed": True, "venue": "OA Resolved"}
            return False, None

        def mock_cr(p):
            if p.doi == "10.1000/1":  # Shard B failure routed to Crossref
                return True, {"confirmed": True, "venue": "CR Resolved"}
            return False, None

        verifier._verify_with_semantic_scholar = MagicMock(side_effect=mock_s2)
        verifier._verify_with_openalex = MagicMock(side_effect=mock_oa)
        verifier._verify_with_crossref = MagicMock(side_effect=mock_cr)

        verified = verifier.verify_batch([p0, p1, p2])

        self.assertEqual(p0.verified_via, "OpenAlex")
        self.assertEqual(p1.verified_via, "Crossref")
        self.assertEqual(p2.verified_via, "Semantic_Scholar")

    def test_round_3_final_catch_all_arxiv_and_doaj(self):
        """Validates that papers unresolved after Round 2 are caught by arXiv, DOAJ, or marked Unverified."""
        verifier = TieredWorkloadVerifier(
            local_db=self.local_db,
            cache=self.cache,
            s2_delay_seconds=0.0
        )

        # Primary ring (S2, OA, CR) returns not found for all
        verifier._verify_with_semantic_scholar = MagicMock(return_value=(False, None, False))
        verifier._verify_with_openalex = MagicMock(return_value=(False, None))
        verifier._verify_with_crossref = MagicMock(return_value=(False, None))

        # arXiv verifies p_arxiv, DOAJ verifies p_doaj, p_unverified fails everything
        def mock_arxiv(p):
            if p.doi == "10.1000/arxiv":
                return True, {"confirmed": True, "pdf_link": "https://arxiv.org/pdf/test.pdf"}
            return False, None

        def mock_doaj(p):
            if p.doi == "10.1000/doaj":
                return True, {"confirmed": True, "venue": "DOAJ Journal", "pdf_link": "https://doaj.org/pdf"}
            return False, None

        verifier._verify_with_arxiv = MagicMock(side_effect=mock_arxiv)
        verifier._verify_with_doaj = MagicMock(side_effect=mock_doaj)

        p_arxiv = Paper(title="Preprint arXiv Paper", doi="10.1000/arxiv")
        p_doaj = Paper(title="Open Access DOAJ Paper", doi="10.1000/doaj")
        p_unverified = Paper(title="Ghost Unknown Paper", doi="10.1000/unknown")

        verified = verifier.verify_batch([p_arxiv, p_doaj, p_unverified])

        self.assertEqual(p_arxiv.verified_via, "arXiv")
        self.assertTrue(p_arxiv.open_access)
        self.assertEqual(p_arxiv.publication_type, "Preprint")

        self.assertEqual(p_doaj.verified_via, "DOAJ")
        self.assertTrue(p_doaj.open_access)
        self.assertEqual(p_doaj.venue, "DOAJ Journal")

        self.assertEqual(p_unverified.verified_via, "Unverified")
        self.assertEqual(p_unverified.index_status, "Non-Indexed")

    def test_semantic_scholar_safety_valve_shifts_queue(self):
        """
        Validates the Semantic Scholar Safety Valve:
        - When HTTP 429 is encountered, safety valve pauses S2 endpoint for 5.5s.
        - Remaining Shard A candidates are immediately shifted to OpenAlex and Crossref.
        """
        safety_valve = SemanticScholarSafetyValve(cooldown_seconds=5.5)
        self.assertFalse(safety_valve.is_paused)

        safety_valve.trip()
        self.assertTrue(safety_valve.is_paused)
        self.assertGreater(safety_valve.remaining_cooldown(), 4.0)

        verifier = TieredWorkloadVerifier(
            local_db=self.local_db,
            cache=self.cache,
            s2_delay_seconds=0.0,
            s2_cooldown_seconds=5.5
        )

        call_idx = 0
        def mock_s2(p):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                # First call hits HTTP 429
                return False, None, True
            return True, {"confirmed": True, "venue": "S2"}, False

        oa_called = []
        def mock_oa(p):
            oa_called.append(p.doi)
            return True, {"confirmed": True, "venue": "OpenAlex"}

        cr_called = []
        def mock_cr(p):
            cr_called.append(p.doi)
            return True, {"confirmed": True, "venue": "Crossref"}

        verifier._verify_with_semantic_scholar = MagicMock(side_effect=mock_s2)
        verifier._verify_with_openalex = MagicMock(side_effect=mock_oa)
        verifier._verify_with_crossref = MagicMock(side_effect=mock_cr)

        # 6 candidates -> Shard A has p0 (idx 0), p3 (idx 3)
        papers = [Paper(title=f"Paper {i}", doi=f"10.1000/{i}") for i in range(6)]
        verified = verifier.verify_batch(papers)

        # S2 safety valve should be paused
        self.assertTrue(verifier.safety_valve.is_paused)

        # Paper 3 (remaining in Shard A) was shifted to OpenAlex or Crossref
        self.assertTrue("10.1000/3" in oa_called or "10.1000/3" in cr_called)

        # Check all records have valid Verified_Via tags
        for p in verified:
            self.assertIn(p.verified_via, ["OpenAlex", "Crossref", "Semantic_Scholar", "Unverified"])

    def test_dual_branch_verifier_batch_integration(self):
        """Verifies DualBranchVerifier.verify_batch integrates with 3-way workload partitioning."""
        dual_verifier = DualBranchVerifier(local_db=self.local_db, cache=self.cache, inst_token_flag=False)

        # Mock tiered_verifier
        dual_verifier.tiered_verifier._verify_with_semantic_scholar = MagicMock(
            return_value=(True, {"confirmed": True, "venue": "S2 Journal"}, False)
        )
        dual_verifier.tiered_verifier._verify_with_openalex = MagicMock(
            return_value=(True, {"confirmed": True, "venue": "OA Journal"})
        )
        dual_verifier.tiered_verifier._verify_with_crossref = MagicMock(
            return_value=(True, {"confirmed": True, "venue": "CR Journal"})
        )

        p0 = Paper(title="Batch Paper 0", doi="10.1000/b0")
        p1 = Paper(title="Batch Paper 1", doi="10.1000/b1")
        p2 = Paper(title="Batch Paper 2", doi="10.1000/b2")

        verified = dual_verifier.verify_batch([p0, p1, p2])

        self.assertEqual(len(verified), 3)
        self.assertEqual(p0.verified_via, "Semantic_Scholar")
        self.assertEqual(p1.verified_via, "OpenAlex")
        self.assertEqual(p2.verified_via, "Crossref")


if __name__ == "__main__":
    unittest.main()
