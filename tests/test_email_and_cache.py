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
