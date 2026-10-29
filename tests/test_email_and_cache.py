"""
tests/test_email_and_cache.py - Tests for cache purging and redesigned rich email templates.
"""

import os
import time
import unittest
from pathlib import Path

from cache_cleaner import purge_stale_cache
from email_service import (
    parse_run_config_tags,
    get_morning_questionnaire_template,
    email_dispatcher
)


class TestCacheCleaner(unittest.TestCase):
    def setUp(self):
        self.test_cache_dir = "cache/test_cleaner_dir"
        os.makedirs(self.test_cache_dir, exist_ok=True)

        self.fresh_file = os.path.join(self.test_cache_dir, "fresh_cache.json")
        self.stale_file = os.path.join(self.test_cache_dir, "stale_cache.json")

        with open(self.fresh_file, "w") as f:
            f.write('{"status": "fresh"}')
        with open(self.stale_file, "w") as f:
            f.write('{"status": "stale"}')

        # Backdate the stale file mtime by 50 hours (180,000s > 172,800s TTL)
        old_time = time.time() - 180000
        os.utime(self.stale_file, (old_time, old_time))

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_cache_dir):
            try:
                shutil.rmtree(self.test_cache_dir)
            except Exception:
                pass

    def test_purge_stale_cache(self):
        purged = purge_stale_cache(ttl_seconds=172800, target_dirs=[self.test_cache_dir])
        self.assertEqual(purged, 1)
        self.assertFalse(os.path.exists(self.stale_file))
        self.assertTrue(os.path.exists(self.fresh_file))

    def test_lru_size_capped_eviction(self):
        """Verifies that exceeding the size ceiling evicts oldest files by LRU."""
        from services.cache.manager import CacheManager
        f1 = os.path.join(self.test_cache_dir, "f1.json")
        f2 = os.path.join(self.test_cache_dir, "f2.json")
        f3 = os.path.join(self.test_cache_dir, "f3.json")

        with open(f1, "w") as f:
            f.write("x" * 1024)
        with open(f2, "w") as f:
            f.write("y" * 1024)
        with open(f3, "w") as f:
            f.write("z" * 1024)

        os.utime(f1, (time.time() - 300, time.time() - 300))
        os.utime(f2, (time.time() - 200, time.time() - 200))
        os.utime(f3, (time.time() - 100, time.time() - 100))

        mgr = CacheManager(cache_dir=self.test_cache_dir)
        evicted = mgr.enforce_size_cap(max_bytes=2100)
        self.assertGreaterEqual(evicted, 1)
        self.assertFalse(os.path.exists(f1))
        self.assertTrue(os.path.exists(f3))

    def test_compact_data_only_payload_truncation(self):
        """Verifies raw API payload dumps with huge author graphs/references are truncated."""
        from services.cache.manager import truncate_to_compact_payload
        raw_payload = {
            "doi": "10.1109/53.1",
            "title": "Fuzzy Systems Control",
            "year": "2024",
            "venue": "IEEE TFS",
            "indexed_scopus": True,
            "indexed_wos": False,
            "open_access_url": "https://example.com/oa.pdf",
            "raw_reference_list": [{"id": f"ref_{i}", "citations": [1, 2, 3]} for i in range(500)],
            "full_author_graph": [{"name": f"Author_{i}", "h_index": 20, "institutions": ["A", "B"]} for i in range(100)],
            "telemetry_data": {"ip": "1.2.3.4", "session_token": "abc"}
        }
        compact = truncate_to_compact_payload(raw_payload)
        self.assertEqual(compact["doi"], "10.1109/53.1")
        self.assertEqual(compact["title"], "Fuzzy Systems Control")
        self.assertEqual(compact["year"], 2024)
        self.assertTrue(compact["indexed_scopus"])
        self.assertFalse(compact["indexed_wos"])
        self.assertEqual(compact["open_access_url"], "https://example.com/oa.pdf")
        self.assertNotIn("raw_reference_list", compact)
        self.assertNotIn("full_author_graph", compact)
        self.assertNotIn("telemetry_data", compact)


class TestEmailConfigParser(unittest.TestCase):
    def test_parse_rich_morning_questionnaire_template(self):
        """Verifies parsing of the rich Section 2 morning template with colons and emojis."""
        template = get_morning_questionnaire_template("2026-10-28")
        config, errors = parse_run_config_tags(template)

        self.assertEqual(errors, [])
        self.assertIsNotNone(config)
        self.assertEqual(config["run_name"], "Run_2026-10-28_01")
        self.assertEqual(config["run_type"], "Automated")
        self.assertEqual(config["location"], "HITS Campus")
        self.assertEqual(config["harvest_quota"], 250)
        self.assertEqual(config["quota_strictness"], "Strict")
        self.assertEqual(len(config["topics"]), 2)
        self.assertEqual(config["topics"][0], "Fuzzy Machine Learning")
        self.assertEqual(config["topics"][1], "Graph Neural Networks")
        self.assertEqual(len(config["subtopics_map"]["Fuzzy Machine Learning"]), 5)

    def test_single_line_quick_trigger_format(self):
        """Verifies parsing of Section 3.A single-line trigger format."""
        single_line = "[RUN_TODAY]: Yes | [TOPIC]: Fuzzy Neural Networks | [QUOTA]: 100"
        config, errors = parse_run_config_tags(single_line)

        self.assertEqual(errors, [])
        self.assertIsNotNone(config)
        self.assertEqual(config["topics"], ["Fuzzy Neural Networks"])
        self.assertEqual(config["harvest_quota"], 100)

    def test_parameter_adjustment_validation_errors(self):
        """Verifies detection of boundary overflows (>500 quota, >5 subtopics) for Section 4 notices."""
        overflow_body = """
        [NAME_OF_RUN]: Overflow_Run
        [TOPIC_1]: Deep Learning
        [T1_SUBTOPICS]: Sub1, Sub2, Sub3, Sub4, Sub5, Sub6, Sub7
        [PAPERS_PER_TOPIC]: 700
        """
        config, errors = parse_run_config_tags(overflow_body)
        self.assertIsNone(config)
        self.assertGreater(len(errors), 0)

        error_text = " ".join(errors)
        self.assertIn("700 papers", error_text)
        self.assertIn("ceiling is 500", error_text)
        self.assertIn("7 subtopics", error_text)
        self.assertIn("Maximum allowed is 5", error_text)

    def test_validation_error_on_missing_topics(self):
        email_body = """
        [NAME_OF_RUN]: Empty_Topic_Run
        [BATCH_RUN]: No
        [PAPERS_PER_TOPIC]: 250
        """
        config, errors = parse_run_config_tags(email_body)
        self.assertIsNone(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("topic" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
