"""
batch_runner.py - Backward compatibility wrapper delegating to core.batch_runner.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from core.batch_runner import *
from core.batch_runner import ResilientBatchRunner, logger

__all__ = ["ResilientBatchRunner", "logger"]
