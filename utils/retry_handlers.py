"""
utils/retry_handlers.py - Robust HTTP retry handler with rate limit awareness and credential rotation.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import random
import logging
from email.utils import parsedate_to_datetime
from typing import Callable, Optional
import requests

logger = logging.getLogger("RetryHandler")


def _parse_retry_after(header_val: Optional[str]) -> Optional[float]:
    """
    Parses a Retry-After header which may be integer/float delta seconds,
    a Unix epoch timestamp (> 1e9), or an HTTP date string (RFC 2822 / 7231).
    """
    if not header_val:
        return None
    header_val = header_val.strip()
    try:
        val = float(header_val)
        # Handle Unix epoch timestamp vs relative delta seconds
        if val > 1_000_000_000:
            return max(0.0, val - time.time())
        return max(0.0, val)
    except ValueError:
        pass
    try:
        target_dt = parsedate_to_datetime(header_val)
        delay = target_dt.timestamp() - time.time()
        return max(0.0, delay)
    except Exception:
        return None


def execute_with_429_retry(
    request_fn: Callable[[], requests.Response],
    max_retries: int = 4,
    initial_backoff: float = 1.5,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0,
    service_name: str = "External Service",
    on_retry_callback: Optional[Callable[[requests.Response, int], None]] = None,
) -> Optional[requests.Response]:
    """
    Executes an HTTP request function with retry handling on HTTP 429, transient 5xx errors,
    and network dropouts. Supports token rotation callbacks and honors Retry-After headers.

    Args:
        request_fn: Zero-argument callable executing the HTTP request.
        max_retries: Total number of retry attempts before giving up.
        initial_backoff: Initial sleep duration in seconds.
        backoff_factor: Exponential multiplier applied after each retry.
        max_backoff: Upper bound for any single backoff wait duration.
        service_name: Label used for contextual log messages.
        on_retry_callback: Hook triggered on retryable response: fn(response, attempt).
                           Used to rotate API keys or update rate limiter state.

    Returns:
        The final requests.Response object, or None if retries are exhausted by exceptions.
    """
    attempt = 0
    current_backoff = initial_backoff

    while attempt <= max_retries:
        resp: Optional[requests.Response] = None
        try:
            resp = request_fn()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            if attempt == max_retries:
                logger.error(
                    f"[{service_name}] Request failed after {max_retries} retries due to network error: {exc}"
                )
                return None

            sleep_duration = min(max_backoff, current_backoff + random.uniform(0.1, 0.5))
            logger.warning(
                f"[{service_name}] Network error ({exc.__class__.__name__}). Retrying in {sleep_duration:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(sleep_duration)
            current_backoff = min(max_backoff, current_backoff * backoff_factor)
            attempt += 1
            continue
        except requests.RequestException as exc:
            logger.error(f"[{service_name}] Non-retryable request exception: {exc}")
            return None

        # Success or non-retryable client error
        if resp.status_code not in (429, 500, 502, 503, 504):
            return resp

        # Max retries reached
        if attempt == max_retries:
            logger.error(
                f"[{service_name}] Max retries reached ({max_retries}). Final status: {resp.status_code}"
            )
            return resp

        # Fire credential rotation or monitoring callback
        if on_retry_callback:
            try:
                on_retry_callback(resp, attempt)
            except Exception as cb_err:
                logger.warning(f"[{service_name}] Error during on_retry_callback: {cb_err}")

        # Compute delay: prioritize server-provided Retry-After over standard backoff
        server_retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
        if server_retry_after is not None:
            if server_retry_after > 120.0:
                logger.error(
                    f"[{service_name}] Daily quota or rate window exhausted "
                    f"(Retry-After: {server_retry_after:.0f}s > 120s). Aborting retries immediately."
                )
                return resp
            wait_seconds = min(max_backoff, server_retry_after)
        else:
            jitter = random.uniform(0.1, 0.5)
            wait_seconds = min(max_backoff, current_backoff + jitter)
            current_backoff = min(max_backoff, current_backoff * backoff_factor)

        logger.warning(
            f"⚠️ [{service_name}] HTTP {resp.status_code}. Retrying in {wait_seconds:.2f}s "
            f"(attempt {attempt + 1}/{max_retries})..."
        )
        time.sleep(wait_seconds)
        attempt += 1

    return resp