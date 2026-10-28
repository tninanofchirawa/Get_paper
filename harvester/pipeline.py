"""
harvester/pipeline.py - Asynchronous accumulator pipeline fixing the 83/87 item freezing bug.
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
from harvester.deduplication import DeduplicationEngine

logger = logging.getLogger("HarvestingPipeline")


class AsyncHarvestingPipeline:
    """
    Coordinates multi-provider parallel harvesting via an asynchronous accumulator loop.
    Guarantees active pagination until `len(unique_papers) >= target_quota` OR all providers are exhausted.
    Eliminates the 83/87 item freezing bug.
    """

    def __init__(self, harvesters: Optional[List[BaseAsyncHarvester]] = None):
        if harvesters is not None:
            self.harvesters = harvesters
        else:
            self.harvesters = [
                OpenAlexHarvester(),
                CrossrefHarvester(),
                SemanticScholarHarvester(),
                ArxivHarvester()
            ]

    async def harvest(
        self,
        query: str,
        target_quota: int = cfg.DEFAULT_QUOTA,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None,
        quota_strictness: str = "Strict",
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[List[Paper], Dict[str, int]]:
        """
        Executes active accumulator pagination across all providers.
        Returns: (retained_unique_papers, metrics_dict)
        """
        deduper = DeduplicationEngine(similarity_threshold=0.90)
        provider_states: Dict[str, Dict[str, Any]] = {}

        for h in self.harvesters:
            provider_states[h.name] = {
                "harvester": h,
                "page_token": None,
                "has_more": True,
                "fetched_count": 0,
                "consecutive_empty": 0
            }

        logger.info(f"=== Starting Active Accumulator Harvest | Query: '{query}' | Target Quota: {target_quota} ===")
        print(f"[Pipeline] Starting Active Accumulator Harvest | Query: '{query}' | Target: {target_quota} papers ({quota_strictness} mode)")

        round_num = 0
        max_empty_rounds = 4

        connector = aiohttp.TCPConnector(limit=25, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Active accumulator loop: Keep running until quota met OR all providers exhausted
            while len(deduper.unique_papers) < target_quota:
                round_num += 1
                active_providers = [
                    p for p in provider_states.values()
                    if p["has_more"] and p["consecutive_empty"] < max_empty_rounds
                ]

                if not active_providers:
                    logger.info("[Pipeline] All provider queries exhausted. Ending accumulator loop.")
                    print("[Pipeline] All provider queries exhausted. Ending accumulator loop.")
                    break

                deficit = target_quota - len(deduper.unique_papers)
                # Calculate batch chunk per active provider with 35% redundancy to overcome deduplication drops
                chunk_per_provider = max(25, int((deficit / len(active_providers)) * 1.35))
                chunk_per_provider = min(chunk_per_provider, 100)

                async def fetch_provider_chunk(state: Dict[str, Any]):
                    h: BaseAsyncHarvester = state["harvester"]
                    try:
                        papers, next_token, has_more = await h.fetch_page(
                            session=session,
                            query=query,
                            page_token=state["page_token"],
                            page_size=chunk_per_provider,
                            year_range=year_range,
                            doc_filter=doc_filter
                        )
                        state["page_token"] = next_token
                        state["has_more"] = has_more
                        state["fetched_count"] += len(papers)
                        if len(papers) == 0:
                            state["consecutive_empty"] += 1
                        else:
                            state["consecutive_empty"] = 0
                        return h.name, papers
                    except Exception as e:
                        logger.error(f"[{h.name}] Fetch chunk failed: {e}")
                        state["consecutive_empty"] += 1
                        return h.name, []

                # Execute page fetch across active providers concurrently
                tasks = [fetch_provider_chunk(s) for s in active_providers]
                batch_results = await asyncio.gather(*tasks)

                round_raw_count = 0
                for provider_name, papers in batch_results:
                    round_raw_count += len(papers)
                    if papers:
                        deduper.add_papers(papers)

                logger.info(
                    f"[Round {round_num}] Fetched {round_raw_count} raw entries. "
                    f"Total Unique Retained: {len(deduper.unique_papers)} / {target_quota}"
                )
                print(
                    f"  -> Round {round_num}: +{round_raw_count} raw entries | "
                    f"Progress: {len(deduper.unique_papers)}/{target_quota} unique retained "
                    f"(Duplicates dropped: {deduper.duplicates_removed_count})"
                )

                if progress_callback:
                    progress_callback(query, len(deduper.unique_papers), target_quota)

                # In Fast/Capped mode, stop after first round of harvesting
                if quota_strictness.lower() in ("fast", "fast/capped", "capped") and round_num >= 1:
                    logger.info("[Pipeline] Capped mode enabled: stopping after initial harvest pass.")
                    print("[Pipeline] Capped mode enabled: stopping after initial harvest pass.")
                    break

                # If no papers were added this round across all providers, check if exhausted
                if round_raw_count == 0:
                    all_exhausted = all(not p["has_more"] or p["consecutive_empty"] >= max_empty_rounds for p in provider_states.values())
                    if all_exhausted:
                        logger.info("[Pipeline] All providers have zero further records. Terminating accumulator.")
                        break

        # Trim strictly to target_quota if requested, while retaining deduplication logs
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
