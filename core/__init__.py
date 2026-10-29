"""
core - Orchestration engines, analysis models, batch runners, and database persistence.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from core.models import Paper, clean_matching_title, sanitize_doi
from core.database import DatabaseManager, db
from core.analyzer import PaperAnalyzer, FUZZY_CATEGORIES
from core.batch_runner import ResilientBatchRunner

__all__ = [
    "Paper",
    "clean_matching_title",
    "sanitize_doi",
    "DatabaseManager",
    "db",
    "PaperAnalyzer",
    "FUZZY_CATEGORIES",
    "ResilientBatchRunner",
]
