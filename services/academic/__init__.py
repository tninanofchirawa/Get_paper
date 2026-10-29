"""
services/academic - Isolated academic API client modules.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from services.academic.semantic_scholar import SemanticScholarClient
from services.academic.crossref import CrossrefClient
from services.academic.openalex import OpenAlexClient
from services.academic.arxiv import ArxivClient

__all__ = [
    "SemanticScholarClient",
    "CrossrefClient",
    "OpenAlexClient",
    "ArxivClient",
]
