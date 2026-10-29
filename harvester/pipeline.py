"""
harvester/pipeline.py - Asynchronous literature harvesting pipeline with round-robin provider rotation.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Callable, Any, Tuple

import aiohttp

from config import cfg
from harvester.models import Paper
from harvester.base import BaseAsyncHarvester
from harvester.openalex import OpenAlexHarvester
from harvester.crossref import CrossrefHarvester
from harvester.arxiv import ArxivHarvester
from harvester.semantic_scholar import SemanticScholarHarvester
from harvester.core_ac import CoreHarvester
from harvester.distributor import ActiveQueryDistributor, ProviderState
from harvester.deduplication import DeduplicationEngine

logger = logging.getLogger("HarvestingPipeline")


class AsyncHarvestingPipeline:
    """
    Coordinates multi-source literature harvesting via active provider rotation.
    Features:
    - Active Query Distribution: Cycles across OpenAlex, Crossref, Semantic Scholar,
      arXiv, and CORE instead of treating them as emergency-only circuit-breaker fallbacks.
    - Global Cumulative Rate Limiting: Respects strict 1 req/sec limit on Semantic Scholar endpoints.
    - Dynamic Cooldown: 5.5s safety buffer with exponential scaling, immediately rotating to alternate
      aggregators when an API hits rate limits or returns empty.
    - Active Accumulator Loop: Eliminates pagination freezes by continuing across providers until target quota.
    """

    def __init__(self, harvesters: Optional[List[BaseAsyncHarvester]] = None):
        if harvesters is not None:
            self.harvesters = harvesters
        else:
            self.harvesters = [
                OpenAlexHarvester(),
                CrossrefHarvester(),
                SemanticScholarHarvester(),
                ArxivHarvester(),
                CoreHarvester()
            ]

    async def harvest(
        self,
        query: str,
        target_quota: int = cfg.DEFAULT_QUOTA,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None,
        quota_strictness: str = "Strict",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> Tuple[List[Paper], Dict[str, int]]:
        """
        Executes active round-robin query rotation across academic aggregators.
        Returns: (retained_unique_papers, metrics_dict)
        """
        deduper = DeduplicationEngine(similarity_threshold=0.90)
        distributor = ActiveQueryDistributor(self.harvesters)

        logger.info(f"=== Starting Active Round-Robin Harvest | Query: '{query}' | Quota: {target_quota} ===")
        print(f"[Pipeline] Starting Active Round-Robin Harvest | Query: '{query}' | Target: {target_quota} papers ({quota_strictness} mode)")

        round_num = 0

        async def _execute_distributor(active_session: aiohttp.ClientSession):
            nonlocal round_num

            while len(deduper.unique_papers) < target_quota:
                round_num += 1

                if distributor.is_all_exhausted():
                    logger.info("[Pipeline] All provider queries exhausted. Ending accumulator loop.")
                    print("[Pipeline] All provider queries exhausted. Ending accumulator loop.")
                    break

                provider_state, wait_sec = distributor.select_next_provider()
                if not provider_state:
                    # All active providers currently in cooldown
                    sleep_duration = max(0.1, min(wait_sec, 2.0))
                    logger.debug(f"[Pipeline] All providers in cooldown. Waiting {sleep_duration:.2f}s...")
                    await asyncio.sleep(sleep_duration)
                    continue

                h: BaseAsyncHarvester = provider_state.harvester
                deficit = target_quota - len(deduper.unique_papers)
                chunk_size = max(25, min(100, int(deficit * 1.25)))

                try:
                    logger.debug(f"[Pipeline] Querying '{h.name}' for chunk of {chunk_size}...")
                    papers, next_token, has_more = await h.fetch_page(
                        session=active_session,
                        query=query,
                        page_token=provider_state.page_token,
                        page_size=chunk_size,
                        year_range=year_range,
                        doc_filter=doc_filter
                    )

                    if not papers:
                        distributor.record_empty(provider_state)
                    else:
                        distributor.record_success(provider_state, papers, next_token, has_more)
                        raw_added, dups_dropped, unique_count = deduper.add_papers(papers)
                        print(
                            f"  -> [{h.name}] +{len(papers)} raw ({raw_added - dups_dropped} unique) | "
                            f"Progress: {unique_count}/{target_quota} (Duplicates dropped: {deduper.duplicates_removed_count})"
                        )

                        if progress_callback:
                            progress_callback(query, len(deduper.unique_papers), target_quota)

                except Exception as e:
                    distributor.record_failure(provider_state, e)

                if quota_strictness.lower() in ("fast", "fast/capped", "capped") and round_num >= len(self.harvesters):
                    logger.info("[Pipeline] Capped mode enabled: stopping after initial round-robin pass.")
                    print("[Pipeline] Capped mode enabled: stopping after initial round-robin pass.")
                    break

        if session is not None:
            await _execute_distributor(session)
        else:
            connector = aiohttp.TCPConnector(limit=25, ttl_dns_cache=300)
            async with aiohttp.ClientSession(connector=connector) as managed_session:
                await _execute_distributor(managed_session)

        final_papers = deduper.unique_papers[:target_quota]
        metrics = {
            "raw_scraped": deduper.raw_scraped_count,
            "duplicates_removed": deduper.duplicates_removed_count,
            "verified_retained": len(final_papers),
        }

        print(
            f"[Pipeline Finished] Raw Scraped: {metrics['raw_scraped']} | "
            f"Duplicates Removed: {metrics['duplicates_removed']} | "
            f"Retained: {metrics['verified_retained']}"
        )
        return final_papers, metrics
