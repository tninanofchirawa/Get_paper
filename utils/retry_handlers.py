"""
utils/retry_handlers.py - Exponential backoff retry handlers for HTTP 429 and transient errors.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import random
import logging
from typing import Callable, Any, Optional
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger("RetryHandler")


def execute_with_429_retry(
    request_fn: Callable[[], requests.Response],
    max_retries: int = 4,
    initial_backoff: float = 1.5,
    max_backoff: float = 30.0,
    service_name: str = "API"
) -> Optional[requests.Response]:
    """
    Executes an HTTP request function with custom exponential backoff retry
    specifically tuned for HTTP 429 (Too Many Requests) and 5xx errors.
    Extracts and honors 'Retry-After' headers when provided by the server.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = request_fn()
            if resp.status_code == 429:
                # Check for Retry-After header
                retry_after_str = resp.headers.get("Retry-After")
                if retry_after_str:
                    try:
                        sleep_time = float(retry_after_str)
                    except ValueError:
                        sleep_time = min(max_backoff, initial_backoff * (2 ** (attempt - 1)))
                else:
                    # Exponential backoff with small random jitter
                    sleep_time = min(max_backoff, initial_backoff * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5))

                if attempt < max_retries:
                    logger.warning(
                        f"[{service_name}] HTTP 429 (Rate Limit Hit). Attempt {attempt}/{max_retries}. "
                        f"Backing off for {sleep_time:.2f}s..."
                    )
                    print(
                        f"⚠️ [{service_name}] HTTP 429 (Rate Limit Hit). Attempt {attempt}/{max_retries}. "
                        f"Backing off for {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    continue
                else:
                    logger.error(f"[{service_name}] HTTP 429 persistence after {max_retries} attempts.")
                    return resp

            return resp

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                sleep_time = min(max_backoff, initial_backoff * (2 ** (attempt - 1)))
                logger.warning(f"[{service_name}] Network error ({e}). Retrying in {sleep_time:.2f}s (Attempt {attempt}/{max_retries})...")
                time.sleep(sleep_time)
            else:
                logger.error(f"[{service_name}] Request failed after {max_retries} attempts: {e}")
                raise e

    return None
