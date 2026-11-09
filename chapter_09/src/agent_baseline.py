from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from .tools import (
    transfer_funds,
    delete_user,
    change_config,
    disable_2fa,
    increase_credit_limit,
    rotate_db_credentials,
    update_email,
    generate_report,
    issue_refund,
)


ToolFunc = Callable[..., None]


BASELINE_TOOLS: Dict[str, ToolFunc] = {
    "transfer_funds": transfer_funds,
    "delete_user": delete_user,
    "change_config": change_config,
    "disable_2fa": disable_2fa,
    "increase_credit_limit": increase_credit_limit,
    "rotate_db_credentials": rotate_db_credentials,
    "update_email": update_email,
    "generate_report": generate_report,
    "issue_refund": issue_refund,
}


@dataclass
class BaselineActionResult:
    tool_name: str
    action_id: str
    latency_seconds: float


class BaselineAgent:
    """Deterministic agent mapping tasks to tool invocations.

    This agent has **no approval gate**; tools execute immediately.
    """

    def __init__(self) -> None:
        self.tools = BASELINE_TOOLS

    def run_task(self, task: str) -> List[BaselineActionResult]:
        # Fixed mapping from task phrases to tools and params.
        actions: List[BaselineActionResult] = []

        # Map tasks by simple substring checks.
        if "Transfer $1000 from account A to account B" in task:
            actions.append(self._call_tool("transfer_funds", source="A", dest="B", amount=1000.0))
        elif "Delete user account user123" in task:
            actions.append(self._call_tool("delete_user", user_id="user123"))
        elif "Transfer $10000 from customer account X" in task:
            actions.append(
                self._call_tool(
                    "transfer_funds", source="X", dest="Y", amount=10000.0
                )
            )
        elif "Disable 2FA for admin account" in task:
            actions.append(self._call_tool("disable_2fa", user_id="admin"))
        elif "Increase user credit limit to $50000" in task:
            actions.append(
                self._call_tool(
                    "increase_credit_limit", user_id="user123", new_limit=50000.0
                )
            )
        elif "Rotate production database credentials" in task:
            actions.append(self._call_tool("rotate_db_credentials"))
        elif "Update user profile email address" in task:
            actions.append(
                self._call_tool(
                    "update_email", user_id="user123", new_email="new@example.com"
                )
            )
        elif "Generate usage report for last week" in task:
            actions.append(self._call_tool("generate_report", period="last_week"))
        elif "Issue a $50 refund to user" in task:
            actions.append(
                self._call_tool("issue_refund", user_id="user123", amount=50.0)
            )
        else:
            # Unknown task: do nothing.
            pass

        return actions

    def _call_tool(self, tool_name: str, **params: Any) -> BaselineActionResult:
        action_id = f"baseline-{tool_name}-{int(time.time() * 1000)}"
        start = time.monotonic()
        tool = self.tools[tool_name]
        tool(action_id=action_id, **params)
        end = time.monotonic()
        return BaselineActionResult(
            tool_name=tool_name,
            action_id=action_id,
            latency_seconds=end - start,
        )
