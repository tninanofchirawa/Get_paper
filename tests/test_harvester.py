"""
tests/test_harvester.py - Tests for harvesting, sanitization, deduplication, active distributor, and accumulator.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from harvester.models import Paper, sanitize_doi, sanitize_title, clean_matching_title, clean_year
from harvester.deduplication import DeduplicationEngine
from harvester.distributor import ActiveQueryDistributor, ProviderState
from harvester.pipeline import AsyncHarvestingPipeline
from harvester.base import BaseAsyncHarvester


def run_coro_sync(coro):
    """Synchronously steps an async coroutine without requiring an IOCP/socket loop."""
    stack = [coro]
    val = None
    while stack:
        top = stack[-1]
        try:
            if hasattr(top, "__await__"):
                it = top.__await__()
                stack[-1] = it
                top = it
            res = top.send(val)
            val = None
            if hasattr(res, "__await__"):
                stack.append(res)
        except StopIteration as e:
            stack.pop()
            val = e.value
    return val


class TestHarvesterModels(unittest.TestCase):
    def test_sanitize_doi(self):
        self.assertEqual(sanitize_doi("https://doi.org/10.1109/2.53"), "10.1109/2.53")
        self.assertEqual(sanitize_doi("doi:10.1016/j.fss.2005.05.036."), "10.1016/j.fss.2005.05.036")
        self.assertEqual(sanitize_doi("10.1007/978-3-030-94066-9"), "10.1007/978-3-030-94066-9")
        self.assertEqual(sanitize_doi("Not verified"), "")
        self.assertEqual(sanitize_doi(None), "")

    def test_sanitize_title(self):
        raw = "<b>A \\textbf{Novel} Fuzzy Approach to \\textit{Neural} Networks</b> &amp; Systems"
        expected = "A Novel Fuzzy Approach to Neural Networks & Systems"
        self.assertEqual(sanitize_title(raw), expected)

    def test_clean_year(self):
        self.assertEqual(clean_year("Published 2024-05-12"), "2024")
        self.assertEqual(clean_year("1988"), "1988")
        self.assertEqual(clean_year("N/A"), "")


class TestDeduplicationEngine(unittest.TestCase):
    def test_exact_doi_deduplication(self):
        deduper = DeduplicationEngine()
        p1 = Paper(title="Fuzzy Logic Control", doi="10.1109/53.1")
        p2 = Paper(title="Fuzzy Logic Control Systems", doi="10.1109/53.1")

        self.assertTrue(deduper.add_paper(p1))
        self.assertFalse(deduper.add_paper(p2))
        self.assertEqual(deduper.raw_scraped_count, 2)
        self.assertEqual(deduper.duplicates_removed_count, 1)
        self.assertEqual(len(deduper.unique_papers), 1)

    def test_fuzzy_title_deduplication(self):
        deduper = DeduplicationEngine(similarity_threshold=0.90)
        p1 = Paper(title="Adaptive Neuro-Fuzzy Inference System for Medical Diagnosis", doi="")
        p2 = Paper(title="Adaptive Neuro Fuzzy Inference Systems for Medical Diagnosis", doi="")

        self.assertTrue(deduper.add_paper(p1))
        self.assertFalse(deduper.add_paper(p2))
        self.assertEqual(deduper.duplicates_removed_count, 1)

    def test_distinct_metrics_tracking(self):
        deduper = DeduplicationEngine()
        papers = [
            Paper(title="Paper One", doi="10.1/1"),
            Paper(title="Paper Two", doi="10.1/2"),
            Paper(title="Paper One Duplicate", doi="10.1/1"),
            Paper(title="Paper Three", doi="10.1/3"),
        ]
        raw, dups, retained = deduper.add_papers(papers)
        self.assertEqual(raw, 4)
        self.assertEqual(dups, 1)
        self.assertEqual(retained, 3)
        self.assertEqual(deduper.metrics["raw_scraped"], 4)
        self.assertEqual(deduper.metrics["duplicates_removed"], 1)
        self.assertEqual(deduper.metrics["unique_retained"], 3)


class MockHarvester(BaseAsyncHarvester):
    """Mock harvester yielding paged results to test accumulator loop."""
    def __init__(self, name: str, pages: list):
        super().__init__(name, rate_limit_per_second=100.0)
        self.pages = pages
        self.page_idx = 0

    async def fetch_page(self, session, query, page_token=None, page_size=50, year_range=None, doc_filter=None):
        if self.page_idx < len(self.pages):
            papers = self.pages[self.page_idx]
            self.page_idx += 1
            has_more = self.page_idx < len(self.pages)
            return papers, str(self.page_idx), has_more
        return [], None, False


class TestActiveQueryDistributor(unittest.TestCase):
    def test_round_robin_provider_rotation(self):
        h1 = MockHarvester("SourceA", pages=[[Paper(title="A1", doi="10.1/a1")]])
        h2 = MockHarvester("SourceB", pages=[[Paper(title="B1", doi="10.1/b1")]])
        h3 = MockHarvester("SourceC", pages=[[Paper(title="C1", doi="10.1/c1")]])

        distributor = ActiveQueryDistributor([h1, h2, h3])

        p1, _ = distributor.select_next_provider()
        self.assertEqual(p1.name, "SourceA")
        p2, _ = distributor.select_next_provider()
        self.assertEqual(p2.name, "SourceB")
        p3, _ = distributor.select_next_provider()
        self.assertEqual(p3.name, "SourceC")
        # Wraps back to SourceA
        p4, _ = distributor.select_next_provider()
        self.assertEqual(p4.name, "SourceA")

    def test_dynamic_cooldown_and_immediate_rotation(self):
        h1 = MockHarvester("Primary", pages=[])
        h2 = MockHarvester("FallbackOpenAlex", pages=[[Paper(title="O1", doi="10.1/o1")]])

        distributor = ActiveQueryDistributor([h1, h2])

        p1, _ = distributor.select_next_provider()
        self.assertEqual(p1.name, "Primary")

        # Simulate 429/failure on Primary -> triggers cooldown
        distributor.record_failure(p1, Exception("429 Too Many Requests"))
        self.assertGreater(p1.cooldown_until, 0)
        self.assertGreaterEqual(p1.backoff_seconds, 5.5)

        # Next query rotates immediately to FallbackOpenAlex rather than hammering Primary
        p2, _ = distributor.select_next_provider()
        self.assertEqual(p2.name, "FallbackOpenAlex")


class TestAccumulatorLoopFix(unittest.TestCase):
    def test_83_87_freezing_bug_fix(self):
        """
        Tests that when a single page returns fewer items than target quota (e.g. 50 items),
        the accumulator loop continues paginating until target quota (e.g. 85 items) is met.
        """
        import hashlib
        page1 = [Paper(title=f"Study_{i}_{hashlib.md5(f'a_{i}'.encode()).hexdigest()}", doi=f"10.1000/{i}") for i in range(1, 51)]
        page2 = [Paper(title=f"Study_{i}_{hashlib.md5(f'b_{i}'.encode()).hexdigest()}", doi=f"10.1000/{i}") for i in range(51, 101)]

        mock_h = MockHarvester("MockProvider", pages=[page1, page2])
        pipeline = AsyncHarvestingPipeline(harvesters=[mock_h])

        target_quota = 85
        results, metrics = run_coro_sync(pipeline.harvest(query="test", target_quota=target_quota, session=MagicMock()))

        self.assertEqual(len(results), target_quota)
        self.assertEqual(metrics["raw_scraped"], 100)
        self.assertEqual(metrics["verified_retained"], target_quota)


if __name__ == "__main__":
    unittest.main()
