from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .pending_store import ActionState, PendingAction, PendingActionStore
from .risk_scoring import RiskScorer


@dataclass
class ApprovalResult:
    status: str  # "executed", "denied", "timeout", "bypassed"
    action_id: Optional[str]
    latency_seconds: float


class ApprovalGateway:
    """Approval gateway wrapping sensitive tools.

    - High/medium risk: go through pending store and human approval.
    - Low risk: execute immediately (bypass gate) but still measured.
    """

    def __init__(
        self,
        store: PendingActionStore,
        risk_scorer: RiskScorer,
        tools: Dict[str, Callable[..., None]],
        approve_callback: Callable[[str], None],
        timeout_seconds: float,
    ) -> None:
        self.store = store
        self.risk_scorer = risk_scorer
        self.tools = tools
        self.approve_callback = approve_callback
        self.timeout_seconds = timeout_seconds

    def submit_and_wait(self, tool_name: str, **params: Any) -> ApprovalResult:
        risk = self.risk_scorer.score(tool_name)
        start = time.monotonic()
        if risk == "low":
            # Direct execution without gating, but still uses an action_id.
            action_id = self._new_action_id()
            self._execute_tool(tool_name, action_id, params)
            end = time.monotonic()
            return ApprovalResult(
                status="bypassed",
                action_id=action_id,
                latency_seconds=end - start,
            )

        # For medium/high risk, go through pending store and approval process.
        action_id = self._new_action_id()
        action = PendingAction(
            action_id=action_id,
            tool_name=tool_name,
            params=params,
            risk_level=risk,
            created_at=start,
            timeout_seconds=self.timeout_seconds,
        )
        self.store.create(action)

        # Trigger human approval synchronously via callback.
        self.approve_callback(action_id)

        # Check for timeout or decision.
        now = time.monotonic()
        if action.is_expired(now):
            self.store.mark_timeout(action_id)
            end = time.monotonic()
            return ApprovalResult(
                status="timeout",
                action_id=action_id,
                latency_seconds=end - start,
            )

        # After callback, state should be APPROVED or DENIED.
        if action.state == ActionState.DENIED:
            end = time.monotonic()
            return ApprovalResult(
                status="denied",
                action_id=action_id,
                latency_seconds=end - start,
            )

        if action.state != ActionState.APPROVED:
            # If still pending but not expired, conservatively treat as timeout.
            self.store.mark_timeout(action_id)
            end = time.monotonic()
            return ApprovalResult(
                status="timeout",
                action_id=action_id,
                latency_seconds=end - start,
            )

        # Execute approved action exactly once.
        self._execute_tool(tool_name, action_id, params)
        self.store.mark_executed(action_id)
        end = time.monotonic()
        return ApprovalResult(
            status="executed",
            action_id=action_id,
            latency_seconds=end - start,
        )

    @staticmethod
    def _new_action_id() -> str:
        return str(uuid.uuid4())

    def _execute_tool(self, tool_name: str, action_id: str, params: Dict[str, Any]) -> None:
        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool {tool_name}")
        tool(action_id=action_id, **params)
