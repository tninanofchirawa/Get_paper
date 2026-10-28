"""
harvester package exports.
"""

from harvester.models import Paper, sanitize_doi, sanitize_title, clean_matching_title, clean_year
from harvester.base import BaseAsyncHarvester, AsyncRateLimiter
from harvester.openalex import OpenAlexHarvester
from harvester.crossref import CrossrefHarvester
from harvester.arxiv import ArxivHarvester
from harvester.semantic_scholar import SemanticScholarHarvester
from harvester.deduplication import DeduplicationEngine
from harvester.pipeline import AsyncHarvestingPipeline

__all__ = [
    "Paper",
    "sanitize_doi",
    "sanitize_title",
    "clean_matching_title",
    "clean_year",
    "BaseAsyncHarvester",
    "AsyncRateLimiter",
    "OpenAlexHarvester",
    "CrossrefHarvester",
    "ArxivHarvester",
    "SemanticScholarHarvester",
    "DeduplicationEngine",
    "AsyncHarvestingPipeline",
]
