from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .pending_store import PendingActionStore


@dataclass
class HumanApproverConfig:
    mode: str  # "approve", "deny", "ignore"
    delay_seconds: float
    approver_id: str = "human-1"


class HumanApprover:
    """Deterministic simulator that acts after a fixed delay.

    For simplicity, `process` is called synchronously after the delay. In
    real systems this would be async or event-driven.
    """

    def __init__(self, store: PendingActionStore, config: HumanApproverConfig):
        self.store = store
        self.config = config

    def process(self, action_id: str) -> None:
        # wait for the configured delay in real time to measure latency
        if self.config.delay_seconds > 0:
            time.sleep(self.config.delay_seconds)
        if self.config.mode == "approve":
            self.store.approve(action_id, self.config.approver_id)
        elif self.config.mode == "deny":
            self.store.deny(action_id, self.config.approver_id)
        elif self.config.mode == "ignore":
            # Do nothing; timeout will be handled by caller.
            return
        else:
            raise ValueError(f"Unknown mode {self.config.mode}")
