"""Circuit breaker for broker connections."""

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-broker circuit breaker with configurable thresholds."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        window: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window = window
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._last_failure_time: float = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failures.clear()
            logger.info("Circuit %s CLOSED after successful call", self.name)

    def record_failure(self) -> None:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window]
        self._failures.append(now)
        self._last_failure_time = now
        if len(self._failures) >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit %s OPEN — %d failures in %.0fs",
                self.name,
                len(self._failures),
                self.window,
            )

    def check(self) -> bool:
        """Return True if requests are allowed."""
        return self.state != CircuitState.OPEN
