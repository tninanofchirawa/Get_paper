"""
excel_builder.py - Backward compatibility wrapper delegating to utils.excel_builder.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from utils.excel_builder import *
from utils.excel_builder import StandardizedExcelBuilder

__all__ = ["StandardizedExcelBuilder"]
