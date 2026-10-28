"""
tests/test_database_and_state.py - Tests for SQLite schemas, daily state, and questionnaire state machine.
"""

import os
import unittest
from database import DatabaseManager


class TestDatabaseAndState(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "data/test_pipeline.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = DatabaseManager(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_daily_state_lifecycle(self):
        date_str = "2026-10-28"
        state = self.db.get_or_create_daily_state(date_str)
        self.assertEqual(state["daily_run_completed"], 0)
        self.assertFalse(self.db.is_daily_run_completed(date_str))

        # Mark morning reminder sent
        self.db.mark_reminder_sent("morning", date_str)
        state_updated = self.db.get_or_create_daily_state(date_str)
        self.assertEqual(state_updated["morning_sent"], 1)

        # Mark daily run completed
        self.db.mark_daily_run_completed(date_str)
        self.assertTrue(self.db.is_daily_run_completed(date_str))

        # Test midnight reset
        self.db.reset_daily_state_for_midnight(date_str)
        self.assertFalse(self.db.is_daily_run_completed(date_str))

    def test_conversation_session_state_machine(self):
        session = self.db.create_or_reset_session("email", "researcher@example.com")
        self.assertEqual(session["current_step"], 1)
        self.assertEqual(session["is_complete"], 0)

        # Advance through questionnaire steps
        self.db.update_session(session["session_id"], current_step=2, state_data={"run_name": "TestRun"})
        active = self.db.get_active_session("email", "researcher@example.com")
        self.assertEqual(active["current_step"], 2)
        self.assertEqual(active["state_data"]["run_name"], "TestRun")

        # Complete session
        self.db.update_session(session["session_id"], current_step=15, state_data={"run_name": "TestRun"}, is_complete=True)
        active_after = self.db.get_active_session("email", "researcher@example.com")
        self.assertIsNone(active_after)

    def test_file_queue_lifecycle_states(self):
        run_id = "test_queue_run"
        file_paths = ["file1.csv", "file2.csv"]
        self.db.enqueue_files(run_id, file_paths)

        # Verify QUEUED state
        summary = self.db.get_queue_summary(run_id)
        self.assertEqual(summary["total_files"], 2)
        self.assertEqual(summary["pending"], 2)
        self.assertEqual(summary["completed"], 0)
        self.assertEqual(summary["failed"], 0)

        # Transition file1 to RUNNING
        self.db.update_file_status("file1.csv", "RUNNING")
        summary = self.db.get_queue_summary(run_id)
        self.assertEqual(summary["pending"], 2)

        # Transition file1 to COMPLETED
        self.db.update_file_status("file1.csv", "COMPLETED", processed_count=10, verified_count=8)
        summary = self.db.get_queue_summary(run_id)
        self.assertEqual(summary["completed"], 1)

        # Transition file2 to FAILED
        self.db.update_file_status("file2.csv", "FAILED", error_message="IO error")
        summary = self.db.get_queue_summary(run_id)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["pending"], 0)

    def test_run_history_logging(self):
        run_id = "test_run_1"
        self.db.log_run_start(run_id, "Test Run 1", {"run_type": "Manual", "harvest_quota": 250})
        self.db.log_run_completion(
            run_id=run_id,
            raw_scraped=300,
            duplicates_removed=50,
            verified_retained=250,
            failed_calls=0,
            excel_path="output/test.xlsx",
            status="COMPLETED"
        )
        latest = self.db.get_latest_runs(1)
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["raw_scraped"], 300)
        self.assertEqual(latest[0]["duplicates_removed"], 50)
        self.assertEqual(latest[0]["verified_retained"], 250)
        self.assertEqual(latest[0]["execution_status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
