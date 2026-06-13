"""
Circuit Breaker – Standalone state machine for provider resilience.
CLOSED → OPEN (on threshold) → HALF_OPEN (after timeout) → CLOSED (on success).
Zero stubs. 100% funcional.
"""
import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time: float = 0.0
        self.state = CircuitState.CLOSED

    def record_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (time.time() - self.last_failure_time) >= self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True
