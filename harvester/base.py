"""
harvester/base.py - Asynchronous base harvester with rate limiters and 429 backoff retries.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from config import cfg
from harvester.models import Paper
from utils.retry_handlers import _parse_retry_after

logger = logging.getLogger("HarvesterBase")


class AsyncRateLimiter:
    """Token-bucket rate limiter for client-side API throttling."""

    def __init__(self, max_per_second: float):
        self.interval = 1.0 / max_per_second if max_per_second > 0 else 0.0
        self.lock = asyncio.Lock()
        self.last_request_time = 0.0

    async def acquire(self):
        """Pauses if necessary to maintain requests within allowable rate limit."""
        if self.interval <= 0:
            return
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self.last_request_time = time.monotonic()


class BaseAsyncHarvester(ABC):
    """Abstract base class for asynchronous academic paper collectors."""

    def __init__(self, name: str, rate_limit_per_second: float = 10.0):
        self.name = name
        self.limiter = AsyncRateLimiter(rate_limit_per_second)

    async def get_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = cfg.MAX_RETRIES
    ) -> Optional[Dict[str, Any]]:
        """
        Executes HTTP GET with client-side rate-limiting and resilient 429 exponential backoff.
        Reads 'Retry-After' headers to prevent freezes.
        """
        req_headers = cfg.get_http_headers(self.name.lower())
        if headers:
            req_headers.update(headers)

        for attempt in range(1, retries + 1):
            await self.limiter.acquire()
            try:
                async with session.get(url, params=params, headers=req_headers, timeout=aiohttp.ClientTimeout(total=cfg.DEFAULT_TIMEOUT)) as response:
                    # Handle rate limiting explicitly
                    if response.status == 429:
                        server_delay = _parse_retry_after(response.headers.get("Retry-After"))
                        if server_delay is not None:
                            if server_delay > 120.0:
                                logger.error(
                                    f"[{self.name}] Daily quota or rate window exhausted "
                                    f"(Retry-After: {server_delay:.0f}s > 120s). Aborting harvest requests."
                                )
                                return None
                            sleep_secs = min(60.0, server_delay)
                        else:
                            sleep_secs = min(60.0, cfg.BACKOFF_FACTOR ** attempt)

                        logger.warning(
                            f"[{self.name}] Rate limit 429 encountered. Backing off for {sleep_secs:.1f}s "
                            f"(attempt {attempt}/{retries})."
                        )
                        await asyncio.sleep(sleep_secs)
                        continue

                    # Handle server errors
                    if response.status in (500, 502, 503, 504):
                        sleep_secs = cfg.BACKOFF_FACTOR ** attempt
                        logger.warning(f"[{self.name}] Server error {response.status}. Retrying in {sleep_secs:.1f}s (attempt {attempt}/{retries}).")
                        await asyncio.sleep(sleep_secs)
                        continue

                    if response.status == 200:
                        return await response.json(content_type=None)
                    else:
                        logger.debug(f"[{self.name}] Query returned HTTP {response.status} for URL: {url}")
                        return None

            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                sleep_secs = cfg.BACKOFF_FACTOR ** attempt
                logger.debug(f"[{self.name}] Network error ({e}). Retrying in {sleep_secs:.1f}s (attempt {attempt}/{retries}).")
                if attempt < retries:
                    await asyncio.sleep(sleep_secs)
                else:
                    logger.error(f"[{self.name}] All {retries} retries exhausted for URL: {url}")
                    return None
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error querying {url}: {e}")
                return None

        return None

    @abstractmethod
    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        query: str,
        page_token: Optional[str] = None,
        page_size: int = 50,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None
    ) -> Tuple[List[Paper], Optional[str], bool]:
        """
        Fetches a single page of results.
        Returns: (papers, next_page_token, has_more)
        """
        pass
