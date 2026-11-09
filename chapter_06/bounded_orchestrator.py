from __future__ import annotations

"""Budgeted orchestrator with rate limiting and explicit quotas.

This module implements the treatment condition, wrapping the same agent core
used by the baseline but enforcing:

- Max steps per run
- Max LLM tokens per run
- Max tool calls per run
- Max wall time per run
- Max calls (steps) per minute using a sliding window rate limiter

On any violation, the orchestrator terminates the run with an explicit
stop_reason and metrics including counts of budget and rate limit violations.
"""

import time
from dataclasses import dataclass
from typing import Deque, Optional
from collections import deque

from agents_core import Agent, AgentStepResult


@dataclass
class BudgetConfig:
    max_steps: int
    max_llm_tokens: int
    max_tool_calls: int
    max_calls_per_minute: int
    max_wall_time_s: float


@dataclass
class BudgetCounters:
    steps_taken: int = 0
    llm_tokens_used: int = 0
    tool_calls_made: int = 0
    rate_limit_violations_detected: int = 0
    budget_violations_detected: int = 0


class QuotaViolationError(RuntimeError):
    """Raised when a budget or rate limit would be exceeded."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RateLimiter:
    """Simple sliding-window rate limiter.

    Enforces at most `max_calls_per_minute` events in a 60-second window
    based on `time.monotonic()`.
    """

    def __init__(self, max_calls_per_minute: int) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self._events: Deque[float] = deque()

    def _prune(self, now: float) -> None:
        window_start = now - 60.0
        while self._events and self._events[0] < window_start:
            self._events.popleft()

    def allow(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.monotonic()
        self._prune(now)
        if len(self._events) < self.max_calls_per_minute:
            self._events.append(now)
            return True
        return False


@dataclass
class OrchestratorResult:
    steps_taken: int
    llm_tokens_used: int
    tool_calls_made: int
    wall_time: float
    stop_reason: str
    rate_limit_violations_detected: int
    budget_violations_detected: int


class BudgetedOrchestrator:
    """Orchestrator enforcing budgets on top of a given Agent instance."""

    def __init__(self, budget: BudgetConfig, agent: Agent) -> None:
        self.budget = budget
        self.agent = agent
        self.counters = BudgetCounters()
        self.rate_limiter = RateLimiter(max_calls_per_minute=budget.max_calls_per_minute)

    def _check_budgets_before_step(self, now: float, start: float) -> None:
        elapsed = now - start
        if elapsed > self.budget.max_wall_time_s:
            raise QuotaViolationError("max_wall_time_exceeded")
        if self.counters.steps_taken >= self.budget.max_steps:
            # Exceeded hard step budget before performing another step.
            self.counters.budget_violations_detected += 1
            raise QuotaViolationError("max_steps_exceeded")
        if not self.rate_limiter.allow(now):
            self.counters.rate_limit_violations_detected += 1
            raise QuotaViolationError("rate_limit_exceeded")

    def _check_llm_budget(self, estimated_tokens: int) -> None:
        if self.counters.llm_tokens_used + estimated_tokens > self.budget.max_llm_tokens:
            self.counters.budget_violations_detected += 1
            raise QuotaViolationError("token_budget_exceeded")

    def _check_tool_budget(self) -> None:
        if self.counters.tool_calls_made + 1 > self.budget.max_tool_calls:
            self.counters.budget_violations_detected += 1
            raise QuotaViolationError("tool_call_budget_exceeded")

    def run(self, task: str) -> OrchestratorResult:
        self.agent.reset(task)
        start = time.monotonic()
        observation: Optional[str] = None
        stop_reason = "unknown"

        try:
            while True:
                now = time.monotonic()
                self._check_budgets_before_step(now, start)

                # Ask agent for next step.
                step_result: AgentStepResult = self.agent.step(observation)

                # Check and account for tokens before "executing" the step.
                self._check_llm_budget(step_result.estimated_tokens)
                self.counters.llm_tokens_used += step_result.estimated_tokens

                self.counters.steps_taken += 1

                if step_result.tool_name is not None:
                    self._check_tool_budget()
                    self.counters.tool_calls_made += 1
                    observation = f"tool:{step_result.tool_name}:ok"
                else:
                    observation = step_result.content

                if step_result.stop:
                    stop_reason = "agent_converged"
                    break
        except QuotaViolationError as exc:
            stop_reason = exc.reason

        wall_time = time.monotonic() - start

        return OrchestratorResult(
            steps_taken=self.counters.steps_taken,
            llm_tokens_used=self.counters.llm_tokens_used,
            tool_calls_made=self.counters.tool_calls_made,
            wall_time=wall_time,
            stop_reason=stop_reason,
            rate_limit_violations_detected=self.counters.rate_limit_violations_detected,
            budget_violations_detected=self.counters.budget_violations_detected,
        )
