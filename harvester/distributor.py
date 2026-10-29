"""
harvester/distributor.py - Active Round-Robin Multi-Source Query Distributor.
Coordinates non-burst round-robin queries across OpenAlex, Crossref, Semantic Scholar,
arXiv, and CORE with dynamic cooldown and exponential backoff.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

import aiohttp

from config import cfg
from harvester.models import Paper
from harvester.base import BaseAsyncHarvester

logger = logging.getLogger("QueryDistributor")


@dataclass
class ProviderState:
    """Tracks pagination state, health, and dynamic cooldown for an aggregator."""
    name: str
    harvester: BaseAsyncHarvester
    page_token: Optional[str] = None
    has_more: bool = True
    fetched_count: int = 0
    consecutive_empty: int = 0
    cooldown_until: float = 0.0
    backoff_seconds: float = 5.5  # 5-6s initial buffer


class ActiveQueryDistributor:
    """
    Manages active query distribution across multiple academic aggregators.
    Enforces active provider rotation and dynamic cooldown/backoff rather than
    relying on circuit breaker fallbacks or firing uncontrolled concurrent bursts.
    """

    INITIAL_COOLDOWN_BUFFER: float = 5.5
    MAX_COOLDOWN_SECONDS: float = 30.0
    MAX_EMPTY_ROUNDS: int = 4

    def __init__(self, harvesters: List[BaseAsyncHarvester]):
        self.providers: Dict[str, ProviderState] = {
            h.name: ProviderState(name=h.name, harvester=h)
            for h in harvesters
        }
        self.provider_names: List[str] = list(self.providers.keys())
        self.current_idx: int = 0

    def get_eligible_providers(self) -> List[ProviderState]:
        """Returns list of providers that are not permanently exhausted."""
        return [
            p for p in self.providers.values()
            if p.has_more and p.consecutive_empty < self.MAX_EMPTY_ROUNDS
        ]

    def is_all_exhausted(self) -> bool:
        """Checks if all providers have reached end-of-results or failure ceiling."""
        return len(self.get_eligible_providers()) == 0

    def select_next_provider(self) -> Tuple[Optional[ProviderState], float]:
        """
        Rotates to the next available ready provider using active round-robin.
        If an aggregator is cooling down, immediately rotates to the next one.
        Returns (selected_provider, wait_seconds_if_all_cooling).
        """
        eligible = self.get_eligible_providers()
        if not eligible:
            return None, 0.0

        now = time.monotonic()
        # Check round-robin order
        for _ in range(len(self.provider_names)):
            candidate_name = self.provider_names[self.current_idx % len(self.provider_names)]
            self.current_idx += 1
            state = self.providers[candidate_name]

            if state.has_more and state.consecutive_empty < self.MAX_EMPTY_ROUNDS:
                if now >= state.cooldown_until:
                    return state, 0.0
                else:
                    remaining = state.cooldown_until - now
                    logger.debug(
                        f"[{state.name}] In dynamic cooldown ({remaining:.1f}s remaining). "
                        f"Rotating immediately to next aggregator."
                    )

        # All eligible providers are cooling down; calculate shortest wait
        min_wait = min(max(0.1, p.cooldown_until - now) for p in eligible)
        return None, min_wait

    def record_success(self, state: ProviderState, papers: List[Paper], next_token: Optional[str], has_more: bool):
        """Records successful page retrieval and resets backoff window."""
        state.page_token = next_token
        state.has_more = has_more
        state.fetched_count += len(papers)
        state.consecutive_empty = 0
        state.backoff_seconds = self.INITIAL_COOLDOWN_BUFFER

    def record_empty(self, state: ProviderState):
        """Applies dynamic 5-6s cooldown buffer upon receiving empty result set."""
        now = time.monotonic()
        state.consecutive_empty += 1
        state.cooldown_until = now + state.backoff_seconds
        logger.info(
            f"[{state.name}] 0 records returned. Setting cooldown {state.backoff_seconds:.1f}s "
            f"(consecutive empty: {state.consecutive_empty}/{self.MAX_EMPTY_ROUNDS}). Rotating."
        )
        state.backoff_seconds = min(self.MAX_COOLDOWN_SECONDS, state.backoff_seconds * 1.5)

    def record_failure(self, state: ProviderState, error: Exception):
        """Applies exponential cooldown backoff upon network/rate-limit error."""
        now = time.monotonic()
        state.consecutive_empty += 1
        state.cooldown_until = now + state.backoff_seconds
        logger.warning(
            f"[{state.name}] Request failed: {error}. Setting cooldown {state.backoff_seconds:.1f}s. Rotating."
        )
        state.backoff_seconds = min(self.MAX_COOLDOWN_SECONDS, state.backoff_seconds * 1.5)
