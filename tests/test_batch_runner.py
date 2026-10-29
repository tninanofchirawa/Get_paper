"""
tests/test_batch_runner.py - Verifies deterministic file queue and strict error boundaries.
Fixes the "3 out of 4 Files Processed" bug.
"""

import os
import unittest
from pathlib import Path

from batch_runner import ResilientBatchRunner
from database import db


class TestBatchRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = "output/test_batch_dir"
        os.makedirs(self.test_dir, exist_ok=True)

        # Create 4 test files: 3 valid, 1 corrupted
        self.file1 = os.path.join(self.test_dir, "01_valid_alpha.csv")
        self.file2 = os.path.join(self.test_dir, "02_corrupted_format.csv")
        self.file3 = os.path.join(self.test_dir, "03_valid_beta.csv")
        self.file4 = os.path.join(self.test_dir, "04_valid_gamma.csv")

        with open(self.file1, "w", encoding="utf-8") as f:
            f.write("Title,DOI\nPaper One,10.1000/1\n")

        with open(self.file2, "w", encoding="utf-8") as f:
            f.write("NOT A VALID CSV\x00\xff")  # binary or corrupt data

        with open(self.file3, "w", encoding="utf-8") as f:
            f.write("Title,DOI\nPaper Three,10.1000/3\n")

        with open(self.file4, "w", encoding="utf-8") as f:
            f.write("Title,DOI\nPaper Four,10.1000/4\n")

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except Exception:
                pass

    def test_deterministic_sorting(self):
        queue = ResilientBatchRunner.get_deterministic_file_queue(self.test_dir)
        names = [f.name for f in queue]
        self.assertEqual(names, [
            "01_valid_alpha.csv",
            "02_corrupted_format.csv",
            "03_valid_beta.csv",
            "04_valid_gamma.csv"
        ])

    def test_strict_error_boundary_on_corrupt_file(self):
        """
        Tests that all 4 files are processed. Even when file 2 is corrupted,
        the runner handles it within try/except/finally, records status in SQLite,
        and does NOT silently drop file 3 and 4!
        """
        runner = ResilientBatchRunner()
        # Fast local verification mock to prevent network timeouts during batch unit testing
        runner.verifier.verify_batch = lambda papers, **kwargs: papers
        run_id = "test_batch_run_4files"
        queue = ResilientBatchRunner.get_deterministic_file_queue(self.test_dir)

        db.enqueue_files(run_id, [str(f.resolve()) for f in queue])

        results = []
        for f in queue:
            res = runner.process_single_file(f, run_id, {"run_name": "TestBatch", "location": "Home"})
            results.append(res)

        # All 4 files must be executed and recorded
        self.assertEqual(len(results), 4)
        summary = db.get_queue_summary(run_id)
        self.assertEqual(summary["total_files"], 4)
        self.assertEqual(summary["pending"], 0)  # No dropped tasks!


if __name__ == "__main__":
    unittest.main()
