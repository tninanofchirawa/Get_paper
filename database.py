"""
database.py - Backward compatibility wrapper delegating to core.database.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from core.database import *
from core.database import DatabaseManager, db

__all__ = ["DatabaseManager", "db"]
