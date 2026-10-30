"""
tests/test_modular_services.py - Unit tests for modular services, Semantic Scholar rate limiting,
429 retry backoff, and automated nightly cache purging.
"""

import os
import time
import unittest
from unittest.mock import patch, MagicMock

from config import cfg
from utils.rate_limiters import TokenBucketRateLimiter
from utils.retry_handlers import execute_with_429_retry, _parse_retry_after
from services.academic.semantic_scholar import SemanticScholarClient
from services.academic.openalex import OpenAlexClient
from services.cache.cleaner import purge_nightly_cache
from services.drive.quota import validate_upload_quota_preconditions
from services.drive.mime import get_mime_and_stream
from services.notifications.tag_parser import parse_run_config_tags


class TestRateLimiterAndS2Client(unittest.TestCase):
    def test_token_bucket_pacing(self):
        """Verifies that TokenBucketRateLimiter strictly enforces intervals between calls."""
        # 2 req/s with 0.05s buffer -> interval = 0.55s
        limiter = TokenBucketRateLimiter(rate_limit_per_second=2.0, safety_buffer_seconds=0.05)
        t0 = time.monotonic()
        limiter.acquire()
        limiter.acquire()
        t1 = time.monotonic()
        self.assertGreaterEqual(t1 - t0, 0.50)

    def test_s2_client_headers_contain_api_key(self):
        """Verifies that SemanticScholarClient includes 'x-api-key': os.getenv('S2_API_KEY')."""
        with patch.dict(os.environ, {"S2_API_KEY": "test_s2_token_xyz123"}):
            client = SemanticScholarClient()
            headers = client.get_headers()
            self.assertIn("x-api-key", headers)
            self.assertEqual(headers["x-api-key"], "test_s2_token_xyz123")

    def test_429_exponential_backoff_retry(self):
        """Verifies that execute_with_429_retry catches HTTP 429 and backs off before succeeding."""
        call_count = 0

        def mock_request():
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count < 3:
                resp.status_code = 429
                resp.headers = {"Retry-After": "0.01"}
            else:
                resp.status_code = 200
                resp.json.return_value = {"title": "Success Paper"}
            return resp

        resp = execute_with_429_retry(
            request_fn=mock_request,
            max_retries=4,
            initial_backoff=0.01,
            service_name="TestS2"
        )
        self.assertEqual(call_count, 3)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 200)

    def test_parse_retry_after_epoch_and_delta(self):
        """Verifies _parse_retry_after handles delta seconds, epoch timestamps, and date strings."""
        # 1. Delta seconds
        self.assertEqual(_parse_retry_after("15"), 15.0)
        self.assertEqual(_parse_retry_after("2.5"), 2.5)

        # 2. Unix epoch timestamp > 1e9
        now = time.time()
        future_epoch = str(now + 42.0)
        parsed_delay = _parse_retry_after(future_epoch)
        self.assertIsNotNone(parsed_delay)
        self.assertAlmostEqual(parsed_delay, 42.0, delta=2.0)

        # 3. None / empty / invalid
        self.assertIsNone(_parse_retry_after(None))
        self.assertIsNone(_parse_retry_after(""))
        self.assertIsNone(_parse_retry_after("invalid_header"))

    def test_quota_exhaustion_aborts_immediately(self):
        """Verifies execute_with_429_retry aborts when Retry-After indicates daily quota exhaustion (>120s)."""
        call_count = 0

        def mock_exhausted_request():
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 429
            # OpenAlex quota reset indicator (~6 hours)
            resp.headers = {"Retry-After": "21783"}
            return resp

        resp = execute_with_429_retry(
            request_fn=mock_exhausted_request,
            max_retries=4,
            initial_backoff=0.01,
            service_name="TestOpenAlexQuota"
        )
        # Should abort immediately after attempt 1 rather than sleeping 4 times!
        self.assertEqual(call_count, 1)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 429)

    def test_s2_key_pool_rotation_on_429(self):
        """Verifies SemanticScholarClient rotates through key pool when 429 is encountered."""
        client = SemanticScholarClient()
        client.key_pool = ["key_alpha", "key_beta", "key_gamma"]
        client.current_key_idx = 0

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429

        client._handle_retry_callback(mock_resp_429, 0)
        self.assertEqual(client._get_api_key(), "key_beta")

        client._handle_retry_callback(mock_resp_429, 1)
        self.assertEqual(client._get_api_key(), "key_gamma")

        client._handle_retry_callback(mock_resp_429, 2)
        self.assertEqual(client._get_api_key(), "key_alpha")

    def test_openalex_client_verify_doi_sanitization(self):
        """Verifies OpenAlexClient correctly sanitizes DOIs with various prefixes."""
        client = OpenAlexClient()
        with patch.object(client.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "title": "Clean Title",
                "primary_location": {"source": {"display_name": "Nature"}},
                "open_access": {"is_oa": True, "oa_url": "https://example.com/oa.pdf"}
            }
            mock_get.return_value = mock_resp

            # Case A: with 'doi:' prefix
            res1 = client.verify_doi("doi:10.1038/nature12345")
            self.assertIsNotNone(res1)
            self.assertEqual(res1["doi"], "10.1038/nature12345")
            # Verify URL constructed without duplicate 'doi:'
            called_url = mock_get.call_args[0][0]
            self.assertIn("https://doi.org/10.1038/nature12345", called_url)
            self.assertNotIn("doi:10", called_url)

            # Case B: with 'https://doi.org/' prefix
            res2 = client.verify_doi("https://doi.org/10.1038/nature12345")
            self.assertIsNotNone(res2)
            self.assertEqual(res2["doi"], "10.1038/nature12345")


class TestNightlyCachePurging(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(cfg.CACHE_DIR, "test_nightly_cache")
        os.makedirs(self.test_dir, exist_ok=True)
        self.fresh_file = os.path.join(self.test_dir, "recent_query.json")
        self.stale_file = os.path.join(self.test_dir, "old_artifact.json")

        with open(self.fresh_file, "w") as f:
            f.write('{"data": "fresh"}')
        with open(self.stale_file, "w") as f:
            f.write('{"data": "stale"}')

        # Artificially age the stale file (> 25 hours)
        old_time = time.time() - (26 * 3600)
        os.utime(self.stale_file, (old_time, old_time))

    def tearDown(self):
        for f in [self.fresh_file, self.stale_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if os.path.exists(self.test_dir):
            try:
                os.rmdir(self.test_dir)
            except Exception:
                pass

    def test_nightly_purge_evicts_stale_artifacts(self):
        """Verifies that purge_nightly_cache evicts artifacts older than 24 hours."""
        purged = purge_nightly_cache(target_dirs=[self.test_dir], force_all=False)
        self.assertEqual(purged, 1)
        self.assertTrue(os.path.exists(self.fresh_file))
        self.assertFalse(os.path.exists(self.stale_file))

    def test_manual_override_force_all(self):
        """Verifies that --clear-cache (force_all=True) flushes all files regardless of age."""
        purged = purge_nightly_cache(target_dirs=[self.test_dir], force_all=True)
        self.assertEqual(purged, 2)
        self.assertFalse(os.path.exists(self.fresh_file))
        self.assertFalse(os.path.exists(self.stale_file))


class TestDriveAndNotifications(unittest.TestCase):
    def test_quota_preconditions(self):
        """Verifies that service accounts without folder_id fail preconditions cleanly."""
        self.assertFalse(validate_upload_quota_preconditions("service_account", "", "test@sa.iam.gserviceaccount.com"))
        self.assertTrue(validate_upload_quota_preconditions("service_account", "folder_123", "test@sa.iam.gserviceaccount.com"))
        self.assertTrue(validate_upload_quota_preconditions("oauth_user", "", ""))

    def test_mime_and_gzip(self):
        """Verifies MIME detection for CSV."""
        mime, path, gz = get_mime_and_stream("output/test.csv", enable_gzip=False)
        self.assertEqual(mime, "text/csv")
        self.assertFalse(gz)


if __name__ == "__main__":
    unittest.main()
