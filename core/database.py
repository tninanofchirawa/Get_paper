"""
database.py - SQLite persistence engine for daily state, run history, and deterministic file queues.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import json
import sqlite3
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from config import cfg


class DatabaseManager:
    """Thread-safe SQLite manager with WAL mode and transaction boundaries."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or cfg.DATABASE_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Context manager yielding a SQLite connection with row factories and WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Creates the required tables if they do not exist."""
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_state (
                date TEXT PRIMARY KEY,
                daily_run_completed INTEGER DEFAULT 0,
                morning_sent INTEGER DEFAULT 0,
                afternoon_sent INTEGER DEFAULT 0,
                night_sent INTEGER DEFAULT 0,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                user_identifier TEXT NOT NULL,
                current_step INTEGER DEFAULT 1,
                state_data TEXT DEFAULT '{}',
                is_complete INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS run_history (
                run_id TEXT PRIMARY KEY,
                run_name TEXT,
                run_type TEXT,
                location TEXT,
                is_batch INTEGER DEFAULT 0,
                batch_details TEXT,
                output_mode TEXT,
                target_excel TEXT,
                target_sheet TEXT,
                topics TEXT,
                harvest_quota INTEGER,
                year_range TEXT,
                doc_filter TEXT,
                inst_token_flag INTEGER DEFAULT 0,
                target_repos TEXT,
                quota_strictness TEXT,
                raw_scraped INTEGER DEFAULT 0,
                duplicates_removed INTEGER DEFAULT 0,
                verified_retained INTEGER DEFAULT 0,
                failed_calls INTEGER DEFAULT 0,
                excel_path TEXT,
                drive_file_id TEXT,
                execution_status TEXT,
                created_at TEXT,
                completed_at TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS file_queue (
                file_path TEXT PRIMARY KEY,
                run_id TEXT,
                status TEXT DEFAULT 'QUEUED',
                processed_count INTEGER DEFAULT 0,
                verified_count INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT
            );
            """)

    # --------------------------------------------------------------------------
    # 1. Daily State API
    # --------------------------------------------------------------------------
    def get_or_create_daily_state(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Fetches or creates the daily state record for a given date (defaults to today)."""
        if not date_str:
            date_str = datetime.date.today().isoformat()

        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM daily_state WHERE date = ?", (date_str,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO daily_state (date, daily_run_completed, morning_sent, afternoon_sent, night_sent, last_updated) "
                    "VALUES (?, 0, 0, 0, 0, ?)",
                    (date_str, now_iso)
                )
                row = conn.execute("SELECT * FROM daily_state WHERE date = ?", (date_str,)).fetchone()
            return dict(row)

    def mark_daily_run_completed(self, date_str: Optional[str] = None):
        """Marks daily run as completed, suppressing remaining reminders for the day."""
        if not date_str:
            date_str = datetime.date.today().isoformat()
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            self.get_or_create_daily_state(date_str)
            conn.execute(
                "UPDATE daily_state SET daily_run_completed = 1, last_updated = ? WHERE date = ?",
                (now_iso, date_str)
            )

    def reset_daily_state_for_midnight(self, date_str: Optional[str] = None):
        """Resets daily run state for a fresh day at midnight (00:00 IST)."""
        if not date_str:
            date_str = datetime.date.today().isoformat()
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO daily_state (date, daily_run_completed, morning_sent, afternoon_sent, night_sent, last_updated) "
                "VALUES (?, 0, 0, 0, 0, ?) "
                "ON CONFLICT(date) DO UPDATE SET daily_run_completed = 0, last_updated = excluded.last_updated",
                (date_str, now_iso)
            )

    def mark_reminder_sent(self, tier: str, date_str: Optional[str] = None):
        """Marks a specific reminder tier ('morning', 'afternoon', 'night') as sent."""
        if not date_str:
            date_str = datetime.date.today().isoformat()
        col = f"{tier.lower()}_sent"
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            self.get_or_create_daily_state(date_str)
            conn.execute(
                f"UPDATE daily_state SET {col} = 1, last_updated = ? WHERE date = ?",
                (now_iso, date_str)
            )

    def is_daily_run_completed(self, date_str: Optional[str] = None) -> bool:
        """Returns True if the daily run has been completed."""
        state = self.get_or_create_daily_state(date_str)
        return bool(state.get("daily_run_completed", 0))

    # --------------------------------------------------------------------------
    # 2. Conversation / Intake Sessions
    # --------------------------------------------------------------------------
    def get_active_session(self, channel: str, user_identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves an existing incomplete conversation session for a user."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_sessions WHERE channel = ? AND user_identifier = ? AND is_complete = 0 "
                "ORDER BY created_at DESC LIMIT 1",
                (channel, user_identifier)
            ).fetchone()
            if row:
                d = dict(row)
                d["state_data"] = json.loads(d["state_data"]) if d["state_data"] else {}
                return d
            return None

    def create_or_reset_session(self, channel: str, user_identifier: str, initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a fresh intake session or resets any incomplete session."""
        now_iso = datetime.datetime.now().isoformat()
        clean_id = user_identifier.replace("@", "_").replace(".", "_")[-6:]
        session_id = f"sess_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{clean_id}"
        data_json = json.dumps(initial_data or {})

        with self.get_connection() as conn:
            conn.execute(
                "UPDATE conversation_sessions SET is_complete = 1 WHERE channel = ? AND user_identifier = ? AND is_complete = 0",
                (channel, user_identifier)
            )
            conn.execute(
                "INSERT INTO conversation_sessions (session_id, channel, user_identifier, current_step, state_data, is_complete, created_at, updated_at) "
                "VALUES (?, ?, ?, 1, ?, 0, ?, ?)",
                (session_id, channel, user_identifier, data_json, now_iso, now_iso)
            )
        return {
            "session_id": session_id,
            "channel": channel,
            "user_identifier": user_identifier,
            "current_step": 1,
            "state_data": initial_data or {},
            "is_complete": 0,
            "created_at": now_iso,
            "updated_at": now_iso
        }

    def update_session(self, session_id: str, current_step: int, state_data: Dict[str, Any], is_complete: bool = False):
        """Updates the step and collected parameters of an active questionnaire session."""
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE conversation_sessions SET current_step = ?, state_data = ?, is_complete = ?, updated_at = ? WHERE session_id = ?",
                (current_step, json.dumps(state_data), 1 if is_complete else 0, now_iso, session_id)
            )

    # --------------------------------------------------------------------------
    # 3. Run History API
    # --------------------------------------------------------------------------
    def log_run_start(self, run_id: str, run_name: str, config_dict: Dict[str, Any]) -> str:
        """Logs the start of a harvesting/verification run."""
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO run_history (
                run_id, run_name, run_type, location, is_batch, batch_details,
                output_mode, target_excel, target_sheet, topics, harvest_quota,
                year_range, doc_filter, inst_token_flag, target_repos, quota_strictness,
                execution_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RUNNING', ?)
            """, (
                run_id,
                run_name,
                config_dict.get("run_type", "Manual"),
                config_dict.get("location", "Home"),
                1 if config_dict.get("is_batch") else 0,
                json.dumps(config_dict.get("batch_details", {})),
                config_dict.get("output_mode", "Create New Excel File"),
                config_dict.get("target_excel", ""),
                config_dict.get("target_sheet", "Verified Papers"),
                json.dumps(config_dict.get("topics", [])),
                config_dict.get("harvest_quota", cfg.DEFAULT_QUOTA),
                config_dict.get("year_range", "All Years"),
                config_dict.get("doc_filter", "All"),
                1 if config_dict.get("inst_token_flag") else 0,
                json.dumps(config_dict.get("target_repos", ["OpenAlex", "Crossref"])),
                config_dict.get("quota_strictness", "Strict"),
                now_iso
            ))
        return run_id

    def log_run_completion(
        self,
        run_id: str,
        raw_scraped: int,
        duplicates_removed: int,
        verified_retained: int,
        failed_calls: int,
        excel_path: str,
        drive_file_id: Optional[str] = None,
        status: str = "COMPLETED",
        error_message: str = ""
    ):
        """Updates run record with final metrics upon execution finish."""
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE run_history SET
                raw_scraped = ?,
                duplicates_removed = ?,
                verified_retained = ?,
                failed_calls = ?,
                excel_path = ?,
                drive_file_id = ?,
                execution_status = ?,
                completed_at = ?,
                error_message = ?
            WHERE run_id = ?
            """, (
                raw_scraped,
                duplicates_removed,
                verified_retained,
                failed_calls,
                excel_path,
                drive_file_id or "",
                status,
                now_iso,
                error_message,
                run_id
            ))

    def get_latest_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent runs."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM run_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    # --------------------------------------------------------------------------
    # 4. Deterministic File Queue API (Fixes "3 out of 4 Files Processed" Bug)
    # Lifecycle states: QUEUED -> RUNNING -> COMPLETED or FAILED
    # --------------------------------------------------------------------------
    def enqueue_files(self, run_id: str, file_paths: List[str]):
        """Deterministically registers a list of files into the queue in QUEUED state."""
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            for fp in file_paths:
                conn.execute("""
                INSERT OR REPLACE INTO file_queue (file_path, run_id, status, processed_count, verified_count, started_at)
                VALUES (?, ?, 'QUEUED', 0, 0, ?)
                """, (fp, run_id, now_iso))

    def update_file_status(
        self,
        file_path: str,
        status: str,
        processed_count: int = 0,
        verified_count: int = 0,
        error_message: str = ""
    ):
        """
        Updates execution state of an individual file in the queue.
        Enforces valid lifecycle: QUEUED, RUNNING, COMPLETED, FAILED.
        """
        now_iso = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE file_queue SET
                status = ?,
                processed_count = ?,
                verified_count = ?,
                error_message = ?,
                completed_at = ?
            WHERE file_path = ?
            """, (status, processed_count, verified_count, error_message, now_iso, file_path))

    def get_queue_summary(self, run_id: str) -> Dict[str, Any]:
        """Returns deterministic queue statistics for a run."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM file_queue WHERE run_id = ?", (run_id,)).fetchall()
            total = len(rows)
            completed = sum(1 for r in rows if r["status"] == "COMPLETED")
            failed = sum(1 for r in rows if r["status"] == "FAILED")
            pending = sum(1 for r in rows if r["status"] in ("QUEUED", "PENDING", "RUNNING", "PROCESSING"))
            return {
                "total_files": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "items": [dict(r) for r in rows]
            }


# Global singleton instance
db = DatabaseManager()
