"""
tests/test_email_and_cache.py - Tests for cache purging and 15-tag email configuration parser.
"""

import os
import time
import unittest
from pathlib import Path

from cache_cleaner import purge_stale_cache
from email_service import parse_run_config_tags, get_default_questionnaire_template


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
    def test_parse_valid_default_template(self):
        template = get_default_questionnaire_template("Test_Morning_Run")
        config, errors = parse_run_config_tags(template)

        self.assertEqual(errors, [])
        self.assertIsNotNone(config)
        self.assertEqual(config["run_name"], "Test_Morning_Run")
        self.assertEqual(config["run_type"], "Automated")
        self.assertEqual(config["location"], "Home")
        self.assertEqual(config["harvest_quota"], 250)
        self.assertEqual(config["quota_strictness"], "Strict")
        self.assertEqual(len(config["topics"]), 1)
        self.assertEqual(config["topics"][0], "Fuzzy Logic and Deep Neural Networks")
        self.assertEqual(len(config["subtopics"]), 4)

    def test_enforce_hard_caps(self):
        """Tests that caps (max 5 topics, max 5 subtopics each, max 500 quota) are strictly enforced."""
        email_body = """
        [NAME_OF_RUN] Capped_Run
        [TOPIC_1] Topic 1
        [TOPIC_2] Topic 2
        [TOPIC_3] Topic 3
        [TOPIC_4] Topic 4
        [TOPIC_5] Topic 5
        [TOPIC_6] Topic 6 Should Be Ignored
        [T1_SUBTOPICS] Sub1, Sub2, Sub3, Sub4, Sub5, Sub6 Should Be Dropped
        [PAPERS_PER_TOPIC] 9999
        [QUOTA_STRICTNESS] Fast-Capped
        """
        config, errors = parse_run_config_tags(email_body)
        self.assertEqual(errors, [])
        self.assertIsNotNone(config)
        # Max 5 topics
        self.assertEqual(len(config["topics"]), 5)
        # Max 5 subtopics
        self.assertEqual(len(config["subtopics_map"]["Topic 1"]), 5)
        # Capped quota at 500
        self.assertEqual(config["harvest_quota"], 500)
        self.assertEqual(config["quota_strictness"], "Fast-Capped")

    def test_validation_error_on_missing_topics(self):
        email_body = """
        [NAME_OF_RUN] Empty_Topic_Run
        [BATCH_RUN] No
        [PAPERS_PER_TOPIC] 250
        """
        config, errors = parse_run_config_tags(email_body)
        self.assertIsNone(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("topic" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
