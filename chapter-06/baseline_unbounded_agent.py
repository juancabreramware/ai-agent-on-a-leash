from __future__ import annotations

"""Baseline unbounded agent loop.

Implements a simple orchestration loop around an Agent stub that:
- Repeatedly calls agent.step until the agent indicates stop=True.
- Applies only very high safety caps on steps and wall time to avoid hangs.
- Records metrics: steps_taken, tool_calls_made, llm_tokens_used, wall_time.

No budgets or rate limits are enforced beyond the safety cap.
"""

import time
from dataclasses import dataclass
from typing import Optional

from agents_core import Agent, AgentStepResult


SAFETY_MAX_STEPS = 1000  # High cap, but low enough for CI/sandbox.
SAFETY_MAX_WALL_TIME_S = 30.0


@dataclass
class BaselineRunResult:
    steps_taken: int
    llm_tokens_used: int
    tool_calls_made: int
    wall_time: float
    stop_reason: str


def run_unbounded(task: str, agent: Agent) -> BaselineRunResult:
    agent.reset(task)
    steps_taken = 0
    llm_tokens_used = 0
    tool_calls_made = 0
    stop_reason = "unknown"

    start = time.monotonic()

    observation: Optional[str] = None

    while True:
        now = time.monotonic()
        if now - start > SAFETY_MAX_WALL_TIME_S:
            stop_reason = "hard_timeout"
            break
        if steps_taken >= SAFETY_MAX_STEPS:
            stop_reason = "max_steps_safety_cap"
            break

        result: AgentStepResult = agent.step(observation)
        steps_taken += 1
        llm_tokens_used += result.estimated_tokens

        if result.tool_name is not None:
            # Baseline does not enforce tool budgets; it simply counts.
            tool_calls_made += 1
            # Tools are simulated; we do not model failures here.
            observation = f"tool:{result.tool_name}:ok"
        else:
            observation = result.content

        if result.stop:
            stop_reason = "agent_converged"
            break

    wall_time = time.monotonic() - start

    return BaselineRunResult(
        steps_taken=steps_taken,
        llm_tokens_used=llm_tokens_used,
        tool_calls_made=tool_calls_made,
        wall_time=wall_time,
        stop_reason=stop_reason,
    )
