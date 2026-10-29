"""
analyzer.py - Backward compatibility wrapper delegating to core.analyzer.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from core.analyzer import *
from core.analyzer import PaperAnalyzer, FUZZY_CATEGORIES

__all__ = ["PaperAnalyzer", "FUZZY_CATEGORIES"]
