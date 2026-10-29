# ⚡ Academic API Compliance, Rate Limits & Throttling Guide

## Unified Academic Paper Harvester & Verifier

This guide outlines the concurrency controls, polite pool headers, rate limiting algorithms, and HTTP 429 backoff handlers implemented across all supported academic provider APIs.

---

## 📊 Provider Rate Caps & Concurrency Matrix

| Provider | Protocol / Format | Enforced Rate Cap | Pacing Mechanism | Etiquette / Auth Headers |
|---|---|---|---|---|
| **Semantic Scholar** | Graph REST API | **1.0 req/sec** *(Strict)* | Token Bucket + 1.05s safety buffer | `'x-api-key': os.getenv('S2_API_KEY')` |
| **OpenAlex** | REST API | **10.0 req/sec** | Token Bucket (`AsyncRateLimiter`) | `User-Agent: (mailto:{POLITE_EMAIL})`, `api_key` |
| **Crossref** | REST / Works API | **50.0 req/sec** | Polite Pool Token Bucket | `User-Agent: (mailto:{POLITE_EMAIL})` |
| **arXiv** | Atom XML API | **1 req / 3.0 sec** | Synchronous sleep / interval limiter | `User-Agent: (mailto:{POLITE_EMAIL})` |
| **Elsevier Scopus** | REST API | **1 req / 1.2 sec** | Snail pace limiter | `X-ELS-APIKey`, `X-ELS-Insttoken` |
| **Clarivate WoS** | REST Expanded | **2.0 req/sec** | Token Bucket | `X-ApiKey` |
| **IEEE Xplore** | REST API | **5.0 req/sec** | Token Bucket | `apikey` |

---

## 🧠 Semantic Scholar Graph API: Strict 1 req/sec Architecture

### 1. Environment Variable Configuration
Semantic Scholar enforces strict rate limits on authenticated and unauthenticated queries. Credentials are read strictly from `.env` via the key:
```bash
S2_API_KEY=your_semantic_scholar_api_key_here
```
> [!IMPORTANT]
> API keys are loaded strictly through centralized configuration (`config/`) into `PipelineConfig`. Tokens are never hardcoded into source code or tracked in version control.

### 2. Token Bucket Pacing with 1.05s Safety Buffer
Semantic Scholar limits standard API keys to 1 request per second. Any concurrent or burst traffic immediately results in `HTTP 429 Too Many Requests`.
To eliminate rate-limiting penalties, the pipeline utilizes a process-wide `TokenBucketRateLimiter`:

```python
# services/academic/semantic_scholar.py
_S2_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=1.0, safety_buffer_seconds=0.05)
```

Every outbound query to `/graph/v1/paper/{doi}` or `/graph/v1/paper/search` must acquire a token before dispatching:
```python
self.limiter.acquire()  # Synchronously enforces >= 1.05s interval between requests
```

### 3. HTTP 429 Exponential Backoff Retry Handler
If a transient rate-limit spike or remote server throttle occurs, the request is intercepted by [`execute_with_429_retry`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/utils/retry_handlers.py):
1. Detects `resp.status_code == 429`.
2. Inspects the `Retry-After` response header. If present, sleeps for the specified number of seconds.
3. If absent, applies exponential backoff with random jitter:
   $$\text{sleep\_time} = \min\left(30.0, 1.5 \times 2^{\text{attempt}-1} + \text{uniform}(0.1, 0.5)\right)$$
4. If multiple keys are configured in `SEMANTIC_SCHOLAR_API_KEYS` / `.env`, automatically invokes `_rotate_key()` to switch to an unthrottled key.

### 4. Header Compliance
Every outbound request dispatched by [`SemanticScholarClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/academic/semantic_scholar.py) contains:
```python
headers = {
    "User-Agent": cfg.USER_AGENT,
    "Accept": "application/json",
    "x-api-key": os.getenv("S2_API_KEY")
}
```

---

## 🌐 Other Academic Provider Etiquette Rules

### arXiv Atom XML
- **Policy:** arXiv guidelines mandate at least 3 seconds between successive requests.
- **Implementation:** [`ArxivClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/academic/arxiv.py) enforces a 3.10-second interval (`1.0 / cfg.ARXIV_RATE_DELAY + 0.1s`).
- **Data Format:** Parses XML Atom feeds (`entry`, `title`, `published`, `link`) and extracts direct PDF URLs (`https://arxiv.org/pdf/{id}.pdf`).

### Crossref Polite Pool
- **Policy:** Attaching a valid email address routes requests to Crossref's accelerated Polite Pool (up to 50 requests per second) rather than the congested public pool.
- **Header:** `User-Agent: AcademicHarvester/4.0 (mailto:{POLITE_EMAIL})`.

### OpenAlex REST API
- **Policy:** Free CC0 catalog supporting up to 10 requests per second with mailto etiquette header. Elevated bandwidth is unlocked when `OPENALEX_API_KEY` is provided.
