"""
verifier/local_db.py - Backward-compatible redirect to verifier.local_matcher.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from verifier.local_matcher import LocalDBMatcher, LocalMatcher

__all__ = ["LocalDBMatcher", "LocalMatcher"]
