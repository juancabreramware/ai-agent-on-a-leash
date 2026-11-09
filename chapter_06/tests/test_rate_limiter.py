from __future__ import annotations

"""Unit tests for the RateLimiter used in the bounded orchestrator."""

import time
import unittest

from bounded_orchestrator import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_rate_limiter_enforces_max_calls_per_minute(self) -> None:
        limiter = RateLimiter(max_calls_per_minute=3)

        base = time.monotonic()

        # First three calls within the same timestamp should be allowed.
        self.assertTrue(limiter.allow(base))
        self.assertTrue(limiter.allow(base))
        self.assertTrue(limiter.allow(base))

        # Fourth call within same window should be rejected.
        self.assertFalse(limiter.allow(base))

        # After 61 seconds, old events should be pruned and a new call allowed.
        later = base + 61.0
        self.assertTrue(limiter.allow(later))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
