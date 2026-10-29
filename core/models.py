"""
core/models.py - Core data models and sanitization helpers.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from harvester.models import Paper, clean_matching_title, sanitize_doi

__all__ = [
    "Paper",
    "clean_matching_title",
    "sanitize_doi",
]
