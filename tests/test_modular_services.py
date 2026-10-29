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
from utils.retry_handlers import execute_with_429_retry
from services.academic.semantic_scholar import SemanticScholarClient
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
