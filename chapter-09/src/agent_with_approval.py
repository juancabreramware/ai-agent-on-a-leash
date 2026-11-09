from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .approval_gateway import ApprovalGateway, ApprovalResult
from .pending_store import PendingActionStore
from .risk_scoring import RiskScorer
from .human_simulator import HumanApprover, HumanApproverConfig
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


TOOLS = {
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
class ApprovedActionResult:
    tool_name: str
    approval: ApprovalResult


class AgentWithApproval:
    """Agent whose sensitive tool invocations go through ApprovalGateway."""

    def __init__(
        self,
        store: PendingActionStore,
        risk_scorer: RiskScorer,
        human_config: HumanApproverConfig,
        timeout_seconds: float,
    ) -> None:
        self.store = store
        self.risk_scorer = risk_scorer
        self.timeout_seconds = timeout_seconds
        self.human_approver = HumanApprover(store, human_config)

        def approve_callback(action_id: str) -> None:
            self.human_approver.process(action_id)

        self.gateway = ApprovalGateway(
            store=store,
            risk_scorer=risk_scorer,
            tools=TOOLS,
            approve_callback=approve_callback,
            timeout_seconds=timeout_seconds,
        )

    def run_task(self, task: str) -> List[ApprovedActionResult]:
        actions: List[ApprovedActionResult] = []
        # Deterministic mapping as in BaselineAgent.
        if "Transfer $1000 from account A to account B" in task:
            actions.append(
                self._submit("transfer_funds", source="A", dest="B", amount=1000.0)
            )
        elif "Delete user account user123" in task:
            actions.append(self._submit("delete_user", user_id="user123"))
        elif "Transfer $10000 from customer account X" in task:
            actions.append(
                self._submit(
                    "transfer_funds", source="X", dest="Y", amount=10000.0
                )
            )
        elif "Disable 2FA for admin account" in task:
            actions.append(self._submit("disable_2fa", user_id="admin"))
        elif "Increase user credit limit to $50000" in task:
            actions.append(
                self._submit(
                    "increase_credit_limit", user_id="user123", new_limit=50000.0
                )
            )
        elif "Rotate production database credentials" in task:
            actions.append(self._submit("rotate_db_credentials"))
        elif "Update user profile email address" in task:
            actions.append(
                self._submit(
                    "update_email", user_id="user123", new_email="new@example.com"
                )
            )
        elif "Generate usage report for last week" in task:
            actions.append(
                self._submit("generate_report", period="last_week")
            )
        elif "Issue a $50 refund to user" in task:
            actions.append(
                self._submit("issue_refund", user_id="user123", amount=50.0)
            )
        else:
            pass

        return actions

    def _submit(self, tool_name: str, **params: Any) -> ApprovedActionResult:
        approval = self.gateway.submit_and_wait(tool_name, **params)
        return ApprovedActionResult(tool_name=tool_name, approval=approval)
