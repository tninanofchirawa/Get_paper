"""
tests/test_verifier.py - Tests for CircuitBreaker, LocalDBMatcher, and DualBranchVerifier.
"""

import unittest
from verifier.circuit_breaker import CircuitBreaker
from verifier.local_db import LocalDBMatcher
from verifier.cache import VerificationCache
from verifier.dual_branch import DualBranchVerifier
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


class TestDualBranchVerifier(unittest.TestCase):
    def test_fallback_routing_when_tokens_missing(self):
        verifier = DualBranchVerifier(inst_token_flag=False)
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


if __name__ == "__main__":
    unittest.main()
