"""
utils/circuit_breaker.py - Resilient circuit breaker for academic API services.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger("CircuitBreaker")


class CircuitBreaker:
    """
    Monitors external institutional and academic APIs (Scopus, WoS, IEEE, Semantic Scholar, Crossref).
    Immediately trips on HTTP 401/403 (Invalid Token/IP) or 429 (Quota Exceeded),
    seamlessly routing execution to Open Access / OpenAlex fallback.
    """

    STATE_CLOSED = "CLOSED"       # Normal operation
    STATE_OPEN = "OPEN"           # Tripped - traffic blocked, using fallback
    STATE_HALF_OPEN = "HALF_OPEN" # Testing service recovery

    def __init__(self, service_name: str, failure_threshold: int = 3, recovery_timeout: float = 300.0):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.STATE_CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self.trip_reason = ""

    def is_tripped(self) -> bool:
        """Returns True if the circuit is currently open and requests should bypass to fallback."""
        if self.state == self.STATE_CLOSED:
            return False

        if self.state == self.STATE_OPEN:
            # Check if recovery timeout has elapsed to attempt half-open probe
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"[{self.service_name}] Circuit timeout reached. Attempting HALF-OPEN trial.")
                self.state = self.STATE_HALF_OPEN
                return False
            return True

        # Half-open allows single trial probe
        return False

    def record_success(self):
        """Resets the circuit on successful API response."""
        if self.state != self.STATE_CLOSED:
            logger.info(f"[{self.service_name}] Service recovered. Circuit restored to CLOSED.")
        self.state = self.STATE_CLOSED
        self.consecutive_failures = 0
        self.trip_reason = ""

    def record_failure(self, status_code: Optional[int] = None, error_message: str = "", reason: str = ""):
        """
        Records failure and trips circuit immediately on 401/403/429 or threshold consecutive errors.
        """
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        effective_msg = error_message or reason or "Unknown error"

        # Immediate trip conditions
        if status_code in (401, 403):
            self.state = self.STATE_OPEN
            self.trip_reason = f"Authentication Error (HTTP {status_code}): Invalid Key/Institutional Token or Off-Campus IP."
            logger.warning(f"[{self.service_name}] CIRCUIT TRIPPED IMMEDIATELY! {self.trip_reason} Routing to Open Access fallback.")
            print(f"[{self.service_name}] CIRCUIT TRIPPED IMMEDIATELY! {self.trip_reason} Routing to Open Access fallback.")
            return

        if status_code == 429:
            self.state = self.STATE_OPEN
            self.trip_reason = f"Quota Exceeded (HTTP 429): API rate/quota cap reached."
            logger.warning(f"[{self.service_name}] CIRCUIT TRIPPED! {self.trip_reason} Routing to Open Access fallback.")
            print(f"[{self.service_name}] CIRCUIT TRIPPED! {self.trip_reason} Routing to Open Access fallback.")
            return

        # General failure threshold trip
        if self.consecutive_failures >= self.failure_threshold:
            self.state = self.STATE_OPEN
            self.trip_reason = f"Consecutive Failures ({self.consecutive_failures}): {effective_msg}"
            logger.warning(f"[{self.service_name}] CIRCUIT TRIPPED! {self.trip_reason} Routing to Open Access fallback.")
            print(f"[{self.service_name}] CIRCUIT TRIPPED! {self.trip_reason} Routing to Open Access fallback.")

    @property
    def status_summary(self) -> str:
        """Returns human-readable circuit breaker status."""
        if self.state == self.STATE_CLOSED:
            return "Active (Institutional Token Verified)"
        return f"Tripped -> Fallback to Open Access ({self.trip_reason})"
