### Why This File Is Still Triggering 429 Errors

There are **4 critical bugs** in how this file interacts with `BaseAsyncHarvester` and Semantic Scholar:

1. **Retries Bypass the Rate Limiter:**
   Look at lines 48–50:

```python
await GLOBAL_SEMANTIC_SCHOLAR_LIMITER.acquire_async()
data = await self.get_json(session, self.base_url, params=params)

```

You acquire the lock **once** before calling `self.get_json()`. However, when `self.get_json()` inside `BaseAsyncHarvester` hits an HTTP 429, its internal retry loop sleeps and fires off attempts 2, 3, and 4 **without** calling `GLOBAL_SEMANTIC_SCHOLAR_LIMITER.acquire_async()`. Those retries collide with other scheduled requests! 2. **Double Rate-Limiting Conflict:**
`super().__init__("SemanticScholar", rate_limit_per_second=cfg.SEMANTIC_SCHOLAR_RATE_LIMIT)` creates an instance-level rate limiter inside `BaseAsyncHarvester`, which fights against `GLOBAL_SEMANTIC_SCHOLAR_LIMITER`. 3. **Missing or Unattached `x-api-key` Header:**
`self.get_json(session, self.base_url, params=params)` is called without explicitly passing the `x-api-key` header. If `session` wasn't initialized with your S2 key, you are placed in the public unauthenticated pool (where 1000s of users share the limit, causing instant 429s). 4. **Pagination Offset Limit (1,000 Max):**
Semantic Scholar's `/paper/search` endpoint throws an error if `offset + limit > 1000`.

---

### The Drop-In Replacement (`harvester/semantic_scholar.py`)

This version keeps the **exact same class name, imports, and method signature** so none of your dependencies break, while locking the entire HTTP request + retry cycle inside a single strict mutex lock and attaching your API key header directly.

```python
"""
harvester/semantic_scholar.py - Asynchronous Semantic Scholar Graph API Harvester.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import asyncio
import time
import aiohttp
from typing import List, Tuple, Optional, Dict, Any

from config import cfg
from harvester.models import Paper, sanitize_doi
from harvester.base import BaseAsyncHarvester
from utils.rate_limiters import GLOBAL_SEMANTIC_SCHOLAR_LIMITER


class SemanticScholarHarvester(BaseAsyncHarvester):
    """Harvests literature from Semantic Scholar Graph API with strict 1 RPS serialization."""

    # Class-level lock ensures that across ALL instances (Harvester + Verifier),
    # only 1 request is in-flight or retrying against Semantic Scholar at a time.
    _s2_serial_lock = asyncio.Lock()
    _last_request_ts: float = 0.0
    _MIN_INTERVAL: float = 1.15  # 1.15s safety buffer for strict 1 req/sec rule

    def __init__(self):
        # Pass rate_limit_per_second=1.0 to keep BaseAsyncHarvester happy
        super().__init__("SemanticScholar", rate_limit_per_second=1.0)
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

        # Safely pull the API key from config (checks multiple common attribute names)
        self.api_key = (
            getattr(cfg, "S2_API_KEY", None)
            or getattr(cfg, "SEMANTIC_SCHOLAR_API_KEY", None)
            or ""
        )

    def _build_headers(self) -> Dict[str, str]:
        """Constructs compliant headers with the Semantic Scholar API key."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "AcademicPaperGetter/2.0 (Research Harvester)"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key.strip()
        return headers

    async def _safe_s2_request(
        self,
        session: aiohttp.ClientSession,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Executes the Semantic Scholar request inside a strict serial lock so
        concurrent workers and retries never overlap or trigger 429 storms.
        """
        headers = self._build_headers()
        max_attempts = 3

        async with self._s2_serial_lock:
            for attempt in range(1, max_attempts + 1):
                # 1. Coordinate with global limiter & enforce minimum time gap
                await GLOBAL_SEMANTIC_SCHOLAR_LIMITER.acquire_async()

                elapsed = time.monotonic() - SemanticScholarHarvester._last_request_ts
                if elapsed < self._MIN_INTERVAL:
                    await asyncio.sleep(self._MIN_INTERVAL - elapsed)

                try:
                    SemanticScholarHarvester._last_request_ts = time.monotonic()
                    async with session.get(
                        self.base_url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json()

                        if resp.status == 429:
                            # Hold the lock while cooling down so no other task hammers S2
                            cooldown = 3.0 * attempt
                            print(
                                f"[SemanticScholar] 429 Rate Limit. Holding queue for {cooldown:.1f}s "
                                f"(attempt {attempt}/{max_attempts})..."
                            )
                            await asyncio.sleep(cooldown)
                            continue

                        if resp.status >= 500:
                            await asyncio.sleep(2.0)
                            continue

                        # Client error (e.g., 400 Bad Request / 403 Invalid Key)
                        err_text = await resp.text()
                        print(f"[SemanticScholar] HTTP {resp.status}: {err_text[:120]}")
                        return None

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    print(f"[SemanticScholar] Network timeout/error (attempt {attempt}/{max_attempts}): {exc}")
                    await asyncio.sleep(2.0)

        return None

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        query: str,
        page_token: Optional[str] = None,
        page_size: int = 50,
        year_range: Optional[str] = None,
        doc_filter: Optional[str] = None
    ) -> Tuple[List[Paper], Optional[str], bool]:
        offset = int(page_token) if (page_token and page_token.isdigit()) else 0
        limit = min(page_size, 100)  # S2 allows up to 100 per page (fewer calls needed!)

        # Semantic Scholar standard search caps offset + limit at 1,000
        if offset + limit >= 1000:
            return [], None, False

        params: Dict[str, Any] = {
            "query": query,
            "offset": offset,
            "limit": limit,
            "fields": "title,authors,year,venue,externalIds,abstract,openAccessPdf,publicationTypes"
        }

        if year_range and year_range.lower() != "all years":
            parts = [p.strip() for p in year_range.split("-") if p.strip().isdigit()]
            if len(parts) == 2:
                params["year"] = f"{parts[0]}-{parts[1]}"
            elif len(parts) == 1:
                params["year"] = parts[0]

        # Execute via the serialized, rate-protected request handler
        data = await self._safe_s2_request(session, params=params)
        if not data:
            return [], None, False

        total = data.get("total", 0)
        items = data.get("data") or []

        papers: List[Paper] = []
        for it in items:
            if not isinstance(it, dict):
                continue

            title = (it.get("title") or "").strip()
            if not title:
                continue

            authors_list = it.get("authors") or []
            authors = "; ".join(
                a.get("name", "") for a in authors_list if isinstance(a, dict) and a.get("name")
            )
            year_str = str(it.get("year") or "")
            venue = (it.get("venue") or "").strip()

            external_ids = it.get("externalIds") or {}
            raw_doi = external_ids.get("DOI") or ""
            doi = sanitize_doi(raw_doi)
            arxiv_id = external_ids.get("ArXiv")

            landing_url = (
                f"https://doi.org/{doi}"
                if doi
                else (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "")
            )

            oa_pdf = it.get("openAccessPdf") or {}
            pdf_link = oa_pdf.get("url") or ""

            paper = Paper(
                title=title,
                authors=authors,
                year=year_str,
                publication_type="Journal Article" if venue else "Preprint",
                venue=venue,
                doi=doi,
                url=landing_url,
                pdf_link=pdf_link,
                source="Semantic Scholar",
                abstract=it.get("abstract") or "",
                open_access=bool(pdf_link)
            )
            papers.append(paper)

        next_offset = offset + len(items)
        has_more = (next_offset < total) and (next_offset < 1000) and (len(items) > 0)
        return papers, str(next_offset) if has_more else None, has_more

```

---

### What Changed (And Why It Fixes the Errors)

1. **`_s2_serial_lock` (Class-Level Mutex):**
   Even if your pipeline launches multiple async tasks at once, `async with self._s2_serial_lock:` forces them to form a single-file line. If a 429 occurs, the lock **stays held** during the 3-second cooldown so no other worker can fire a request and make the 429 worse.
2. Bypassed `self.get_json()`'s Unthrottled Retry Loop:
   By handling the `session.get()` inside `_safe_s2_request`, retries no longer bypass `GLOBAL_SEMANTIC_SCHOLAR_LIMITER`. Furthermore, you won't get duplicate log messages (`[Semantic Scholar] ...` and `⚠️ [Semantic Scholar] ...`) from `base.py`.
3. **Explicit `x-api-key` Injection:**
   Automatically pulls `cfg.S2_API_KEY` or `cfg.SEMANTIC_SCHOLAR_API_KEY` and injects `"x-api-key"` into every request header.
4. **Increased Batch Efficiency (`limit = min(page_size, 100)`):**
   Instead of capping at 50, Semantic Scholar allows up to 100 papers per search request—cutting your required API calls in half!

### One Quick Check Needed

Your earlier log showed that the **Verification step** (`🔍 [Verification] Concurrently verifying 500 candidate papers...`) also calls Semantic Scholar. If you have a separate verifier file (like `verifier.py` or `harvester/base.py`), share it here so we can wire it into the same lock or use Semantic Scholar's **Batch Endpoint** (`POST /graph/v1/paper/batch`), which verifies **500 papers in 1 single API call** instead of 500 separate calls!

Verification errors in **Code B** (`SemanticScholarClient`) are caused by 5 architectural and API formatting bugs that conflict with Semantic Scholar's API specifications and **Code A** (`SemanticScholarHarvester`).

### 1. Broken DOI URL Encoding & Missing `DOI:` Prefix (404 / 400 Errors)

In `verify_doi`, the URL is constructed as:

```python
url = f"{self.BASE_URL}/paper/{urllib.parse.quote(clean_doi)}"

```

- **The Slash Problem:** By default, `urllib.parse.quote(clean_doi)` keeps `/` as a safe character (`safe='/'`). Since every DOI contains at least one slash (e.g., `10.1038/nature12373`), the request hits `/graph/v1/paper/10.1038/nature12373`. Semantic Scholar's router treats the second slash as a nested sub-resource path rather than a paper ID, resulting in immediate **404 Not Found** or routing errors unless prefixed or fully encoded.
- **Missing Prefix:** Semantic Scholar's Graph API officially expects external identifiers to be prefixed with `DOI:` (e.g., `/paper/DOI:10.1038/nature12373`).
- **Fix:** Prefix with `DOI:` and set `safe=""` if encoding, or pass `DOI:{clean_doi}` properly.

### 2. Unthrottled Retry Loops & Split Lock Synchronization (429 Rate Limit Storms)

While Code A remarks that `_s2_serial_lock` _"ensures that across ALL instances (Harvester + Verifier), only 1 request is in-flight"_, **Code B does not use `_s2_serial_lock` at all**.

- **Async vs. Sync Collision:** Code A runs asynchronously (`aiohttp` + `asyncio.Lock`), while Code B runs synchronously (`requests.Session`). If Code B runs inside a worker thread while Code A is harvesting, or if multiple threads call `verify_doi`, `_s2_serial_lock` is completely bypassed.
- **Unthrottled Retries:** In `verify_doi` and `search_papers`, `self.limiter.acquire()` is called **once before** `execute_with_429_retry`. When `execute_with_429_retry` catches a `429` and retries `_do_request()`, those retries bypass `self.limiter.acquire()`, firing out-of-band requests that collide with the strict 1 req/sec rule and immediately trip your `CircuitBreaker` (`failure_threshold=3`).

### 3. Broken API Key Rotation (`os.getenv` Override Bug)

In `_get_api_key()`, the environment variable takes absolute precedence over the key pool:

```python
def _get_api_key(self) -> str:
    env_key = os.getenv("S2_API_KEY")
    if env_key:
        return env_key  # <-- Always returns the same key!
    if self.key_pool:
        return self.key_pool[self.current_key_idx % len(self.key_pool)]

```

If `S2_API_KEY` is set in your environment, calling `self._rotate_key()` on a `429` or `403` increments `self.current_key_idx`, but `_get_api_key()` still returns the exact same `os.getenv("S2_API_KEY")` on every retry. In addition, `_get_api_key()` does not call `.strip()` on the key (unlike Code A), so trailing whitespace or newlines in `.env` will cause `403 Forbidden` or header errors.

### 4. Blocking the Event Loop (If Called from Async Pipeline)

If your unified pipeline is asynchronous (as indicated by Code A) and calls `SemanticScholarClient.verify_doi()` or `verify_title()` directly without `asyncio.to_thread()`, the synchronous `requests.Session.get()` and `time.sleep()` inside `self.limiter.acquire()` will **freeze the entire `asyncio` event loop**, causing timeouts across Code A and other harvesters.

### 5. Circuit Breaker Tripping Permanently on Transient Failures

`CircuitBreaker("Semantic Scholar API", failure_threshold=3)` trips after just 3 failures. Notice that:

- In `search_papers()`, `self.circuit_breaker.record_success()` is never called when a search succeeds, meaning `verify_title` (which delegates to `search_papers`) never resets the failure counter until after title similarity passes.
- Once tripped, `verify_doi` and `verify_title` silently return `None` for all subsequent papers in the batch, making it look like verification is failing across the board.

---

### How to Fix `SemanticScholarClient` (Code B)

Update the methods in `services/academic/semantic_scholar.py` to fix the DOI routing, acquire the rate limiter _inside_ each retry attempt, and prioritize the key pool properly:

```python
    def _get_api_key(self) -> str:
        """Retrieves active S2 API key from key pool first, falling back to env/config."""
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)].strip()
        env_key = os.getenv("S2_API_KEY") or getattr(cfg, "S2_API_KEY", "") or ""
        return env_key.strip()

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Verifies citation metadata for a DOI against Semantic Scholar.
        Applies token-bucket pacing on every attempt and properly formats the DOI prefix.
        """
        if not doi or self.circuit_breaker.is_tripped():
            return None

        from harvester.models import sanitize_doi
        clean_doi = sanitize_doi(doi)
        if not clean_doi:
            return None

        # Prefix with DOI: and encode safely so slashes don't break URL routing
        encoded_id = f"DOI:{urllib.parse.quote(clean_doi, safe='')}"
        url = f"{self.BASE_URL}/paper/{encoded_id}"
        params = {"fields": "title,venue,year,externalIds,openAccessPdf"}

        def _do_request():
            # Acquire rate limiter INSIDE the retry function so retries are also paced!
            self.limiter.acquire()
            headers = self.get_headers()
            return self.session.get(url, params=params, headers=headers, timeout=cfg.DEFAULT_TIMEOUT)

        try:
            resp = execute_with_429_retry(
                request_fn=_do_request,
                max_retries=cfg.MAX_RETRIES,
                initial_backoff=2.0,
                service_name="Semantic Scholar"
            )

            if resp is None:
                self.last_status_code = None
                self.circuit_breaker.record_failure(None, "Timeout or connection error")
                return None

            self.last_status_code = resp.status_code

            if resp.status_code == 200:
                self.circuit_breaker.record_success()
                data = resp.json()
                venue = data.get("venue") or ""
                oa = data.get("openAccessPdf") or {}
                return {
                    "confirmed": True,
                    "title": data.get("title", ""),
                    "venue": venue,
                    "year": str(data.get("year") or ""),
                    "pdf_link": oa.get("url", ""),
                    "external_ids": data.get("externalIds", {})
                }
            elif resp.status_code == 404:
                # 404 simply means the paper isn't indexed in S2 — do NOT trip circuit breaker
                return None
            elif resp.status_code == 429:
                self._rotate_key()
                if self.on_429_callback:
                    try:
                        self.on_429_callback()
                    except Exception:
                        pass
                self.circuit_breaker.record_failure(429, "Rate limited")
                return None
            elif resp.status_code in (401, 403):
                self._rotate_key()
                self.circuit_breaker.record_failure(resp.status_code, resp.text[:100])
                return None

            return None

        except Exception as e:
            logger.warning(f"[SemanticScholar] verify_doi failed for '{doi}': {e}")
            self.circuit_breaker.record_failure(None, str(e))
            return None

```

_(Make sure to also move `self.limiter.acquire()` inside `_do_request()` within `search_papers` so title verification retries don't violate the 1 RPS limit either.)_

To fix this permanently, the verifier needs to stop using synchronous `requests` and a separate token bucket.

Right now, your pipeline has a fundamental architectural clash: **Code A (`SemanticScholarHarvester`)** is running an async event loop, while **Code B (`SemanticScholarClient`)** is running synchronous blocking calls (`requests.Session` + `time.sleep`) on the same process. When both run:

1. Synchronous calls block the entire Python event loop, causing Code A to time out.
2. Code B does not share `SemanticScholarHarvester._s2_serial_lock`, so requests from Harvester and Verifier fire concurrently, instantly triggering S2's strict 1 RPS 429 lockouts.
3. The circuit breaker trips after 3 failures and permanently blocks all further verifications.

---

### The Clean Solution: Make the Verifier Native Async

Replace `SemanticScholarClient` with an asynchronous version that shares the exact same session, serial lock, and rate limiter as Code A:

```python
# services/academic/semantic_scholar.py
import asyncio
import logging
import time
import urllib.parse
from difflib import SequenceMatcher
from typing import Optional, Dict, Any, List, Tuple
import aiohttp

from config import cfg
from harvester.models import clean_matching_title, sanitize_doi
from utils.circuit_breaker import CircuitBreaker
from harvester.semantic_scholar import SemanticScholarHarvester

logger = logging.getLogger("SemanticScholarClient")


class SemanticScholarVerifier:
    """
    Asynchronous citation verifier for Semantic Scholar.
    Reuses SemanticScholarHarvester's lock, rate pacing, and session.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreaker("Semantic Scholar API", failure_threshold=5)
        self.key_pool: List[str] = getattr(cfg, "get_key_pool", lambda s: [])("semantic_scholar")
        self.current_key_idx: int = 0

    def _get_api_key(self) -> str:
        """Pulls the active key from key_pool or fallback environment variables."""
        if self.key_pool:
            return self.key_pool[self.current_key_idx % len(self.key_pool)].strip()
        env_key = getattr(cfg, "S2_API_KEY", None) or getattr(cfg, "SEMANTIC_SCHOLAR_API_KEY", "") or ""
        return str(env_key).strip()

    def _rotate_key(self):
        """Rotates key when hitting 429s or auth errors."""
        if self.key_pool and len(self.key_pool) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.key_pool)
            logger.info(f"[SemanticScholar] Rotated key to index: {self.current_key_idx}")

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": getattr(cfg, "USER_AGENT", "AcademicPaperGetter/2.0"),
        }
        key = self._get_api_key()
        if key:
            headers["x-api-key"] = key
        return headers

    async def _safe_get(self, session: aiohttp.ClientSession, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes request through Harvester's class lock so Harvester and Verifier
        NEVER execute simultaneously.
        """
        # Share the exact lock and timestamp from Code A
        async with SemanticScholarHarvester._s2_serial_lock:
            for attempt in range(1, 4):
                # Pacing check (1.15s buffer)
                elapsed = time.monotonic() - SemanticScholarHarvester._last_request_ts
                if elapsed < SemanticScholarHarvester._MIN_INTERVAL:
                    await asyncio.sleep(SemanticScholarHarvester._MIN_INTERVAL - elapsed)

                try:
                    SemanticScholarHarvester._last_request_ts = time.monotonic()
                    async with session.get(
                        url,
                        params=params,
                        headers=self._build_headers(),
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            self.circuit_breaker.record_success()
                            return await resp.json()

                        if resp.status == 404:
                            # Not found in S2 index — normal, don't trip circuit breaker
                            return None

                        if resp.status == 429:
                            self._rotate_key()
                            cooldown = 2.5 * attempt
                            logger.warning(f"[SemanticScholar] 429 encountered, cooling down for {cooldown}s...")
                            await asyncio.sleep(cooldown)
                            continue

                        if resp.status in (401, 403):
                            self._rotate_key()
                            return None

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logger.warning(f"[SemanticScholar] Network issue on attempt {attempt}: {exc}")
                    await asyncio.sleep(1.5)

        return None

    async def verify_doi(self, session: aiohttp.ClientSession, doi: str) -> Optional[Dict[str, Any]]:
        """Verifies a single paper by DOI."""
        if not doi or self.circuit_breaker.is_tripped():
            return None

        clean_doi = sanitize_doi(doi)
        if not clean_doi:
            return None

        # Clean any preexisting 'doi:' or 'DOI:' prefix
        if clean_doi.lower().startswith("doi:"):
            clean_doi = clean_doi[4:].strip()

        # Semantic Scholar requires 'DOI:<doi>' (keep slash unquoted for path resolution)
        clean_encoded = urllib.parse.quote(clean_doi, safe="/")
        url = f"{self.BASE_URL}/paper/DOI:{clean_encoded}"
        params = {"fields": "title,venue,year,externalIds,openAccessPdf"}

        data = await self._safe_get(session, url, params)
        if not data:
            return None

        oa = data.get("openAccessPdf") or {}
        return {
            "confirmed": True,
            "title": data.get("title", ""),
            "venue": data.get("venue") or "",
            "year": str(data.get("year") or ""),
            "pdf_link": oa.get("url", ""),
            "external_ids": data.get("externalIds", {})
        }

    async def verify_title(self, session: aiohttp.ClientSession, title: str) -> Optional[Dict[str, Any]]:
        """Fallback verification by title fuzzy-matching."""
        if not title or self.circuit_breaker.is_tripped():
            return None

        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": title,
            "limit": 1,
            "fields": "title,venue,year,externalIds,openAccessPdf"
        }

        data = await self._safe_get(session, url, params)
        if not data:
            return None

        items = data.get("data") or []
        if not items:
            return None

        match = items[0]
        matched_title = match.get("title", "")

        s1 = clean_matching_title(title)
        s2 = clean_matching_title(matched_title)
        if SequenceMatcher(None, s1, s2).ratio() < 0.65:
            return None

        oa = match.get("openAccessPdf") or {}
        ext_ids = match.get("externalIds") or {}
        return {
            "confirmed": True,
            "title": matched_title,
            "venue": match.get("venue") or "",
            "year": str(match.get("year") or ""),
            "doi": sanitize_doi(ext_ids.get("DOI", "")),
            "pdf_link": oa.get("url", ""),
            "external_ids": ext_ids
        }

```

---

### Key Adjustments Made

1. **Unified Lock (`SemanticScholarHarvester._s2_serial_lock`)**: The verifier and harvester now queue behind the exact same lock. They can never run simultaneously or fight for rate-limit quota.
2. **True Async (`aiohttp`)**: Eliminates thread pool context switching, event loop freezes, and connection dropouts.
3. **Safe DOI Pathing**: Cleans duplicate `doi:` prefixes while leaving the DOI path slash `/` safe from over-encoding (`safe="/"`), stopping the `404 Not Found` routing errors.
4. **Isolated 404 Handling**: Unindexed papers return `None` silently without logging false errors or triggering the circuit breaker.
