from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class ActionState(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"
    EXECUTED = "EXECUTED"


@dataclass
class PendingAction:
    action_id: str
    tool_name: str
    params: Dict[str, Any]
    risk_level: str
    created_at: float
    timeout_seconds: float
    state: ActionState = ActionState.PENDING
    decided_at: Optional[float] = None
    executed_at: Optional[float] = None
    approver_id: Optional[str] = None
    decision: Optional[str] = None

    def is_expired(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.monotonic()
        return self.state == ActionState.PENDING and (
            now - self.created_at >= self.timeout_seconds
        )


class PendingActionStore:
    """In-memory registry of pending actions with state transition checks."""

    def __init__(self) -> None:
        self._actions: Dict[str, PendingAction] = {}

    def create(self, action: PendingAction) -> None:
        if action.action_id in self._actions:
            raise ValueError(f"Action {action.action_id} already exists")
        self._actions[action.action_id] = action

    def get(self, action_id: str) -> PendingAction:
        return self._actions[action_id]

    def _set_state(self, action: PendingAction, new_state: ActionState) -> None:
        valid_transitions = {
            ActionState.PENDING: {
                ActionState.APPROVED,
                ActionState.DENIED,
                ActionState.TIMEOUT,
            },
            ActionState.APPROVED: {ActionState.EXECUTED},
            ActionState.DENIED: set(),
            ActionState.TIMEOUT: set(),
            ActionState.EXECUTED: set(),
        }
        if new_state not in valid_transitions[action.state]:
            raise ValueError(
                f"Illegal state transition {action.state} -> {new_state} for {action.action_id}"
            )
        action.state = new_state

    def approve(self, action_id: str, approver_id: str) -> PendingAction:
        action = self.get(action_id)
        if action.state != ActionState.PENDING:
            raise ValueError("Can only approve PENDING actions")
        action.decision = "APPROVED"
        action.approver_id = approver_id
        action.decided_at = time.monotonic()
        self._set_state(action, ActionState.APPROVED)
        return action

    def deny(self, action_id: str, approver_id: str) -> PendingAction:
        action = self.get(action_id)
        if action.state != ActionState.PENDING:
            raise ValueError("Can only deny PENDING actions")
        action.decision = "DENIED"
        action.approver_id = approver_id
        action.decided_at = time.monotonic()
        self._set_state(action, ActionState.DENIED)
        return action

    def mark_timeout(self, action_id: str) -> PendingAction:
        action = self.get(action_id)
        if action.state != ActionState.PENDING:
            raise ValueError("Can only timeout PENDING actions")
        self._set_state(action, ActionState.TIMEOUT)
        return action

    def mark_executed(self, action_id: str) -> PendingAction:
        action = self.get(action_id)
        if action.state != ActionState.APPROVED:
            raise ValueError("Can only execute APPROVED actions")
        action.executed_at = time.monotonic()
        self._set_state(action, ActionState.EXECUTED)
        return action

    def snapshot_counts(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in ActionState}
        for a in self._actions.values():
            counts[a.state.value] = counts.get(a.state.value, 0) + 1
        return counts

    def items(self):  # for tests
        return self._actions.items()
