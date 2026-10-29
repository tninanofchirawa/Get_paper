"""
verifier/crossref_verifier.py - Crossref API citation verifier.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to isolated services.academic.crossref.CrossrefClient.
"""

from typing import Optional, Dict, Any
from verifier.circuit_breaker import CircuitBreaker
from services.academic.crossref import CrossrefClient


class CrossrefVerifier:
    """Verifies citation metadata and ISSN existence against Crossref REST API."""

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.client = CrossrefClient(circuit_breaker=circuit_breaker)
        self.circuit_breaker = self.client.circuit_breaker

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Queries Crossref by DOI."""
        return self.client.verify_doi(doi)
