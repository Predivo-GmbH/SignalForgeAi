"""Tests for circuit breaker."""

import time

from app.core.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state == CircuitState.CLOSED
    assert cb.check() is True


def test_circuit_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3, window=60.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.check() is True  # Still closed
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.check() is False


def test_circuit_half_open_after_timeout():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.check() is True


def test_circuit_closes_on_success_from_half_open():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_old_failures_expire():
    cb = CircuitBreaker("test", failure_threshold=3, window=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)  # Failures expire
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # Only 1 failure in window
