from __future__ import annotations

"""Tests for budget enforcement by BudgetedOrchestrator."""

import unittest

from agents_core import MisbehavingAgentStub
from bounded_orchestrator import BudgetConfig, BudgetedOrchestrator


class TestBudgetEnforcement(unittest.TestCase):
    def test_steps_budget_is_enforced(self) -> None:
        # Misbehaving agent never converges; orchestrator must use max_steps.
        agent = MisbehavingAgentStub(mode="runaway")
        budget = BudgetConfig(
            max_steps=5,
            max_llm_tokens=10_000,
            max_tool_calls=10,
            max_calls_per_minute=1_000,
            max_wall_time_s=60.0,
        )
        orch = BudgetedOrchestrator(budget, agent)

        result = orch.run("test task")
        self.assertEqual(result.steps_taken, 5)
        self.assertEqual(result.stop_reason, "max_steps_exceeded")
        self.assertGreaterEqual(result.budget_violations_detected, 1)

    def test_tool_call_budget_is_enforced(self) -> None:
        # Agent that always calls a tool every step.
        agent = MisbehavingAgentStub(mode="dos", tool_name="noop_heavy")
        budget = BudgetConfig(
            max_steps=100,
            max_llm_tokens=10_000,
            max_tool_calls=3,
            max_calls_per_minute=1_000,
            max_wall_time_s=60.0,
        )
        orch = BudgetedOrchestrator(budget, agent)

        result = orch.run("dos task")
        self.assertEqual(result.tool_calls_made, 3)
        self.assertEqual(result.stop_reason, "tool_call_budget_exceeded")
        self.assertGreaterEqual(result.budget_violations_detected, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
