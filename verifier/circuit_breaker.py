"""
verifier/circuit_breaker.py - Resilient circuit breaker (Backward Compatibility Wrapper).
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
Delegates to utils.circuit_breaker.
"""

from utils.circuit_breaker import CircuitBreaker

__all__ = ["CircuitBreaker"]
