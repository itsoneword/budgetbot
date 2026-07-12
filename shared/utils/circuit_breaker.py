"""
Minimal in-memory circuit breaker.

Pure synchronous state machine — no I/O, no decorators, no locking.
Concurrent-probe safety is the caller's responsibility (e.g. hold a
single-flight lock around allow()/record_*() when used from async code).
"""
import time
from typing import Callable


class CircuitBreaker:
    """Failure-counting breaker with a cooldown-based half-open probe.

    States:
    - closed: allow() is True; failures increment a counter.
    - open: entered when consecutive failures reach failure_threshold;
      allow() is False until cooldown_seconds elapse.
    - half-open: after the cooldown, allow() returns True (one probe);
      record_success() closes the breaker, record_failure() reopens it
      for another full cooldown.
    """

    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: float = 900,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    def allow(self) -> bool:
        """Whether a call may proceed. Side-effect-free."""
        if self._opened_at is None:
            return True
        return self._clock() - self._opened_at >= self.cooldown_seconds

    def record_success(self) -> None:
        """Reset the breaker to closed."""
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Count a failure; open (or re-open) at the threshold."""
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self._clock()
