"""
verifier/doaj_verifier.py - DOAJ API open access verifier.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from typing import Optional, Dict, Any
from verifier.circuit_breaker import CircuitBreaker
from services.academic.doaj import DoajClient


class DoajVerifier:
    """Verifies open access journal articles against DOAJ API."""

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
        self.client = DoajClient(circuit_breaker=circuit_breaker)
        self.circuit_breaker = self.client.circuit_breaker

    def verify_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        return self.client.verify_doi(doi)

    def verify_title(self, title: str) -> Optional[Dict[str, Any]]:
        return self.client.verify_title(title)
