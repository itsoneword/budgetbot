"""Unit tests for shared.utils.circuit_breaker.CircuitBreaker.

Pure sync tests with an injectable clock — no I/O, no conftest, no asyncio.
Run with: pytest tests/shared/test_circuit_breaker.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.utils.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_breaker(clock, threshold=2, cooldown=900):
    return CircuitBreaker(
        failure_threshold=threshold, cooldown_seconds=cooldown, clock=clock
    )


def test_starts_closed():
    breaker = make_breaker(FakeClock())
    assert breaker.allow()


def test_stays_closed_below_threshold():
    breaker = make_breaker(FakeClock())
    breaker.record_failure()
    assert breaker.allow()


def test_opens_at_threshold():
    breaker = make_breaker(FakeClock())
    breaker.record_failure()
    breaker.record_failure()
    assert not breaker.allow()


def test_stays_open_during_cooldown():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(899)
    assert not breaker.allow()


def test_half_open_probe_after_cooldown():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(900)
    assert breaker.allow()


def test_reopens_on_probe_failure():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(900)
    assert breaker.allow()  # half-open probe permitted
    breaker.record_failure()  # probe failed -> reopen for a full cooldown
    assert not breaker.allow()
    clock.advance(899)
    assert not breaker.allow()
    clock.advance(1)
    assert breaker.allow()


def test_success_resets_breaker():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(900)
    breaker.record_success()  # successful probe -> closed
    assert breaker.allow()
    # Counter reset: one new failure must not reopen immediately
    breaker.record_failure()
    assert breaker.allow()
    breaker.record_failure()
    assert not breaker.allow()


def test_success_while_closed_clears_failure_count():
    breaker = make_breaker(FakeClock())
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.allow()
