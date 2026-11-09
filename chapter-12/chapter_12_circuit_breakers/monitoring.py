from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Deque, Optional
from collections import deque
import time


@dataclass
class TaskEvent:
    task_index: int
    task_id: str
    task_type: str
    start_time: float
    end_time: float
    latency_ms: float
    success: bool
    error_type: Optional[str]
    policy_violation: bool
    breaker_state_before: str
    breaker_state_after: str
    shutdown_state: str

    def to_dict(self) -> dict:
        from datetime import datetime

        def iso(ts: float) -> str:
            return datetime.utcfromtimestamp(ts).isoformat() + "Z"

        return {
            "task_index": self.task_index,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "start_time_iso": iso(self.start_time),
            "end_time_iso": iso(self.end_time),
            "latency_ms": float(self.latency_ms),
            "success": bool(self.success),
            "error_type": self.error_type,
            "policy_violation": bool(self.policy_violation),
            "breaker_state_before": self.breaker_state_before,
            "breaker_state_after": self.breaker_state_after,
            "shutdown_state": self.shutdown_state,
        }


@dataclass
class MetricsRecorder:
    """Rolling window metrics used for breaker decisions."""

    window_error_rate: int = 20
    window_latency: int = 10

    latencies_ms: Deque[float] = field(default_factory=deque)
    outcomes: Deque[bool] = field(default_factory=deque)  # True=success, False=failure
    policy_violations: int = 0
    total_tasks: int = 0
    total_failures: int = 0

    def record(self, event: TaskEvent) -> None:
        self.total_tasks += 1
        if not event.success:
            self.total_failures += 1
        if event.policy_violation:
            self.policy_violations += 1

        self.latencies_ms.append(event.latency_ms)
        if len(self.latencies_ms) > self.window_latency:
            self.latencies_ms.popleft()

        self.outcomes.append(event.success)
        if len(self.outcomes) > self.window_error_rate:
            self.outcomes.popleft()

    @property
    def error_rate_window(self) -> float:
        if not self.outcomes:
            return 0.0
        failures = sum(1 for ok in self.outcomes if not ok)
        return failures / len(self.outcomes)

    @property
    def rolling_mean_latency(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def overall_error_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_failures / self.total_tasks


@dataclass
class Monitor:
    recorder: MetricsRecorder

    def record_event(self, event: TaskEvent) -> None:
        self.recorder.record(event)

    @property
    def metrics(self) -> MetricsRecorder:
        return self.recorder


class BreakerState(enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    error_rate_threshold_window_20: float = 0.5
    latency_threshold_window_10_ms: float = 250.0
    min_samples_for_decision: int = 10


@dataclass
class CircuitBreaker:
    config: CircuitBreakerConfig
    state: BreakerState = BreakerState.CLOSED
    open_transitions: int = 0
    first_open_task_index: Optional[int] = None

    def evaluate(self, monitor: Monitor) -> None:
        m = monitor.metrics

        if m.total_tasks < self.config.min_samples_for_decision:
            return

        error_rate = m.error_rate_window
        mean_latency = m.rolling_mean_latency

        should_open = False
        if error_rate > self.config.error_rate_threshold_window_20:
            should_open = True
        if mean_latency > self.config.latency_threshold_window_10_ms:
            should_open = True

        if should_open and self.state != BreakerState.OPEN:
            self.state = BreakerState.OPEN
            self.open_transitions += 1
            if self.first_open_task_index is None:
                self.first_open_task_index = m.total_tasks


@dataclass
class EmergencyShutdownManager:
    policy_violation_shutdown_enabled: bool = True
    reason: Optional[str] = None
    _terminated: bool = False

    @property
    def is_terminated(self) -> bool:
        return self._terminated

    @property
    def state(self) -> str:
        return "TERMINATED" if self._terminated else "ACTIVE"

    def terminate(self, reason: str) -> None:
        if not self._terminated:
            self._terminated = True
            self.reason = reason


def now_ms() -> float:
    return time.monotonic() * 1000.0
