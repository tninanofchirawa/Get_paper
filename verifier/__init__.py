"""
verifier package exports.
"""

from verifier.circuit_breaker import CircuitBreaker
from verifier.local_matcher import LocalDBMatcher, LocalMatcher
from verifier.cache import VerificationCache
from verifier.scopus import ScopusVerifier
from verifier.wos import WebOfScienceVerifier
from verifier.ieee import IEEEXploreVerifier
from verifier.openalex_verifier import OpenAlexVerifier
from verifier.dual_branch import DualBranchVerifier

__all__ = [
    "CircuitBreaker",
    "LocalDBMatcher",
    "LocalMatcher",
    "VerificationCache",
    "ScopusVerifier",
    "WebOfScienceVerifier",
    "IEEEXploreVerifier",
    "OpenAlexVerifier",
    "DualBranchVerifier",
]
