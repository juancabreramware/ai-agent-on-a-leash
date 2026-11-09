from __future__ import annotations

from typing import Dict, Any, List

from baseline_agent.llm_mock import MockLLM
from baseline_agent.tools import ToolRegistry
from .guardrails import PromptClassifier, ToolValidator, SafeInterpreter


class GuardedAgent:
    """Guarded tool-using agent with prompt-injection defenses.

    Differences from BaselineAgent:
    - Applies a simple prompt classifier to user input (and conceptually to
      retrieved documents) to detect injection-like content.
    - Validates tool call structure and arguments before execution.
    - Disallows dangerous tools entirely and checks for risky patterns in
      arguments.
    - Uses a safe interpreter that blocks unsafe calls instead of executing
      them.
    """

    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools
        self.classifier = PromptClassifier()
        self.validator = ToolValidator()
        self.interpreter = SafeInterpreter(self.validator)

    def handle_request(self, *, workload_id: str, user_input: str, llm: MockLLM) -> Dict[str, Any]:
        injection_detected = self.classifier.is_injection_like(user_input)

        # In a real system, the user_input and retrieved docs would be
        # segregated before being passed to the LLM. Here, the mock LLM is
        # deterministic, so we just record the detection signal.
        response = llm.generate(workload_id=workload_id, user_input=user_input)
        tool_call = response.tool_call

        unsafe_executions: List[Dict[str, Any]] = []
        blocked_calls: List[Dict[str, Any]] = []

        # Execute via safe interpreter, which may block the tool call.
        unsafe_exec_list, blocked_list = self.interpreter.execute(self.tools, tool_call)
        unsafe_executions.extend(unsafe_exec_list)
        blocked_calls.extend(blocked_list)

        # If the input itself looked like injection, but the tool call was
        # benign and executed, that's still allowed; we record only actual
        # unsafe executions and blocks in metrics.

        return {
            "unsafe_tool_calls_executed": len(unsafe_executions),
            "unsafe_tool_calls_blocked": len(blocked_calls),
            "benign_tool_calls_blocked": 0,
            "unsafe_tool_executions": unsafe_executions,
            "blocked_tool_calls": blocked_calls,
            "injection_detected": injection_detected,
        }
