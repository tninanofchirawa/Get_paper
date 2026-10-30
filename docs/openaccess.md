That massive backoff time (~**6 hours**, or 21,783 seconds) happens because your retry logic is reading the **Unix epoch timestamp** sent in OpenAlex's `Retry-After` header and treating it as a **relative number of seconds**.

---

### The Cause: Epoch Timestamp vs. Relative Delay

When OpenAlex hits you with an HTTP 429, it responds with a `Retry-After` header. Standard HTTP specifications permit two formats for `Retry-After`:

1. **Relative delta seconds:** e.g., `Retry-After: 30` (wait 30 seconds).
2. **HTTP date / absolute timestamp:** e.g., an epoch timestamp indicating the exact time your daily quota or rate window resets (e.g., midnight UTC).

OpenAlex operates a daily request limit (100,000 requests/day for polite users, or smaller limits for unauthenticated/anonymous IPs). When you hit the daily rate limit or trigger rate throttling, OpenAlex often sends back an absolute timestamp or the remaining seconds until the daily quota reset at 00:00 UTC.

If your code executes something like:

```python
# BUG: If header is an absolute epoch timestamp or until-midnight seconds:
retry_after = float(response.headers.get("Retry-After", 1.0))
time.sleep(retry_after)  # 21,783s is ~6 hours until midnight UTC!

```

21,783 seconds is roughly **6 hours and 3 minutes**, which coincides with how many seconds remain until 00:00 UTC when a daily quota is reached.

---

### How to Fix Your Code

#### 1. Add a Maximum Backoff Cap

Never let an automated script sleep for hours unconditionally. Cap retry delays to a practical ceiling (e.g., 30–60 seconds). If it exceeds that, abort or alert instead of hanging the process:

```python
import time

def parse_retry_after(header_val: str, default: float = 2.0, max_cap: float = 60.0) -> float:
    if not header_val:
        return default
    try:
        val = float(header_val)
        # If the value is absurdly large (e.g. an epoch timestamp > 1e8),
        # calculate the difference against current time
        if val > 1_000_000_000:
            delay = max(0.0, val - time.time())
        else:
            delay = val

        # Cap backoff to prevent multi-hour freezing
        return min(delay, max_cap)
    except (ValueError, TypeError):
        return default

```

#### 2. Join the OpenAlex "Polite Pool"

OpenAlex reserves strict throttling for anonymous requests. If you supply your email in the user agent or `mailto` parameter, you get bumped to the polite tier:

- **Header:** `"User-Agent": "mailto:your-email@example.com"`
- **Query param:** `?mailto=your-email@example.com`

This increases your rate limit up to 10 requests/second and significantly reduces 429 penalties.

#### 3. Handle Daily Limit Exhaustion Gracefully

If you have truly exhausted the daily quota (100k requests), waiting 6 hours to retry attempt 1 of 4 will freeze your pipeline. Check if the delay exceeds your acceptable threshold (e.g., `> 120s`); if so, raise an exception or fail the job cleanly rather than sleeping.
