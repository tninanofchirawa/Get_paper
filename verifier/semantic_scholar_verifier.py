"""
verifier/semantic_scholar_verifier.py - Semantic Scholar API citation verifier.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to isolated services.academic.semantic_scholar.SemanticScholarClient.
"""

from typing import Optional, Dict, Any
from verifier.circuit_breaker import CircuitBreaker
from services.academic.semantic_scholar import SemanticScholarClient


class SemanticScholarVerifier:
    """Verifies citation metadata and external IDs against Semantic Scholar Graph API."""

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.client = SemanticScholarClient(circuit_breaker=circuit_breaker)
        self.circuit_breaker = self.client.circuit_breaker

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Queries Semantic Scholar by DOI."""
        return self.client.verify_doi(doi)

    def verify_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Queries Semantic Scholar by title."""
        return self.client.verify_title(title)
