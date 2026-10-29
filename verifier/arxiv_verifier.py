"""
verifier/arxiv_verifier.py - arXiv API preprint verifier.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to isolated services.academic.arxiv.ArxivClient.
"""

from typing import Optional, Dict, Any
from verifier.circuit_breaker import CircuitBreaker
from services.academic.arxiv import ArxivClient


class ArxivVerifier:
    """Verifies preprints and open access records against arXiv API."""

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.client = ArxivClient(circuit_breaker=circuit_breaker)
        self.circuit_breaker = self.client.circuit_breaker

    def verify_paper(self, title: str, doi: str = "") -> Optional[Dict[str, Any]]:
        """Queries arXiv by DOI or title."""
        return self.client.verify_paper(title, doi)
