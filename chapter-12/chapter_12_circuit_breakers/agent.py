from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .monitoring import (
    BreakerState,
    CircuitBreaker,
    EmergencyShutdownManager,
    Monitor,
    TaskEvent,
)


@dataclass
class Task:
    """Representation of a single task.

    type: one of "success", "slow", "failing", "policy_violation".
    latency_ms: simulated latency in milliseconds.
    """

    task_id: str
    task_type: str
    latency_ms: int


class ToolRunner:
    """Executes simulated tools in-process.

    The behavior is deterministic given the Task fields; it does not use
    randomness or external resources.
    """

    def run_task(self, task: Task) -> TaskEvent:
        start_monotonic = time.monotonic()
        start_wall = time.time()

        # Convert ms to seconds; keep sleep durations small but realistic.
        sleep_s = max(0.0, task.latency_ms / 1000.0)
        time.sleep(sleep_s)

        success = True
        error_type: Optional[str] = None
        policy_violation = False

        if task.task_type == "failing":
            success = False
            error_type = "SimulatedFailure"
        elif task.task_type == "policy_violation":
            # Logical/policy violation without technical error.
            success = True
            policy_violation = True

        end_monotonic = time.monotonic()
        end_wall = time.time()
        latency_ms = (end_monotonic - start_monotonic) * 1000.0

        return TaskEvent(
            task_index=0,  # to be filled by agent/monitor
            task_id=task.task_id,
            task_type=task.task_type,
            start_time=start_wall,
            end_time=end_wall,
            latency_ms=latency_ms,
            success=success,
            error_type=error_type,
            policy_violation=policy_violation,
            breaker_state_before="N/A",
            breaker_state_after="N/A",
            shutdown_state="N/A",
        )


class SimpleAgent:
    """Baseline agent that does not use breaker or shutdown logic.

    It still records metrics through a Monitor for comparability, but ignores
    any control decisions.
    """

    def __init__(self, tool_runner: ToolRunner, monitor: Monitor) -> None:
        self.tool_runner = tool_runner
        self.monitor = monitor

    def run(self, tasks: Iterable[Task]) -> List[TaskEvent]:
        events: List[TaskEvent] = []
        for idx, task in enumerate(tasks, start=1):
            event = self.tool_runner.run_task(task)
            # Fill index and allow Monitor to post-process.
            event.task_index = idx
            self.monitor.record_event(event)
            events.append(event)
        return events


class MonitoredAgent:
    """Agent wrapped with Monitor, CircuitBreaker and EmergencyShutdown.

    Control flow:
    - Before each task: check EmergencyShutdownManager and CircuitBreaker.
    - If TERMINATED or OPEN (with no half-open probe allowed), stop executing.
    - After each task: update Monitor, evaluate breaker, and possibly trigger
      emergency shutdown.
    """

    def __init__(
        self,
        tool_runner: ToolRunner,
        monitor: Monitor,
        breaker: CircuitBreaker,
        shutdown_manager: EmergencyShutdownManager,
    ) -> None:
        self.tool_runner = tool_runner
        self.monitor = monitor
        self.breaker = breaker
        self.shutdown_manager = shutdown_manager

    def run(self, tasks: Iterable[Task]) -> List[TaskEvent]:
        events: List[TaskEvent] = []

        for idx, task in enumerate(tasks, start=1):
            # Emergency shutdown short-circuit.
            if self.shutdown_manager.is_terminated:
                break

            # Circuit breaker gating.
            state_before = self.breaker.state
            if state_before == BreakerState.OPEN:
                # For this experiment we do not model half-open probes.
                break

            # Execute task.
            raw_event = self.tool_runner.run_task(task)
            raw_event.task_index = idx
            raw_event.breaker_state_before = state_before.value
            raw_event.shutdown_state = self.shutdown_manager.state

            # Update metrics, then evaluate breaker.
            self.monitor.record_event(raw_event)

            self.breaker.evaluate(self.monitor)
            state_after = self.breaker.state
            raw_event.breaker_state_after = state_after.value

            # Emergency shutdown on policy violation or sustained open.
            if raw_event.policy_violation and self.shutdown_manager.policy_violation_shutdown_enabled:
                self.shutdown_manager.terminate("policy_violation")
            elif state_after == BreakerState.OPEN and not self.shutdown_manager.is_terminated:
                # Treat breaker opening as a soft emergency; may terminate.
                self.shutdown_manager.terminate("breaker_open")

            raw_event.shutdown_state = self.shutdown_manager.state

            events.append(raw_event)

            if self.shutdown_manager.is_terminated:
                break

        return events
