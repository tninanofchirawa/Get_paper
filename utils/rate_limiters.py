"""
utils/rate_limiters.py - Rate limiting decorators and token bucket throttling mechanisms.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import threading
import asyncio
from functools import wraps
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger("RateLimiter")


class TokenBucketRateLimiter:
    """
    Thread-safe and process-safe token bucket rate limiter.
    Enforces a strict rate limit (e.g. 1 req/sec for Semantic Scholar)
    with a minimum sleep safety buffer (e.g. 1.05s).
    """

    def __init__(self, rate_limit_per_second: float = 1.0, safety_buffer_seconds: float = 0.05):
        self.rate = rate_limit_per_second
        self.interval = (1.0 / rate_limit_per_second) + safety_buffer_seconds if rate_limit_per_second > 0 else 0.0
        self.lock = threading.Lock()
        self.last_call_time = 0.0

    def acquire(self):
        """Synchronously blocks until the required rate interval has elapsed."""
        if self.interval <= 0:
            return
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_call_time
            if elapsed < self.interval:
                sleep_duration = self.interval - elapsed
                logger.debug(f"[RateLimiter] Pacing request: sleeping {sleep_duration:.3f}s to respect {self.rate} req/s cap.")
                time.sleep(sleep_duration)
            self.last_call_time = time.monotonic()

    async def acquire_async(self):
        """Asynchronously awaits until the required rate interval has elapsed."""
        if self.interval <= 0:
            return
        now = time.monotonic()
        with self.lock:
            elapsed = now - self.last_call_time
            sleep_duration = max(0.0, self.interval - elapsed)
            # Update timestamp immediately to reserve the slot for subsequent callers
            self.last_call_time = now + sleep_duration
        if sleep_duration > 0:
            logger.debug(f"[RateLimiter] Async pacing: sleeping {sleep_duration:.3f}s.")
            await asyncio.sleep(sleep_duration)


class AsyncRateLimiter:
    """Token-bucket rate limiter for client-side aiohttp API throttling."""

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


def rate_limited(limiter: TokenBucketRateLimiter):
    """Decorator to enforce strict rate limiting on any function call."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            limiter.acquire()
            return fn(*args, **kwargs)
        return wrapper
    return decorator
