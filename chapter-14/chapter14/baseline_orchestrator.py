from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .store import InMemoryStore
from .workloads import WorkloadAgent, WorkloadProfile


@dataclass
class BaselineRunInfo:
    steps_executed: int


class BaselineOrchestrator:
    """Simple orchestrator with no checkpoints or invariant checks."""

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def _apply_action(self, store: InMemoryStore, action: Dict[str, Any]) -> None:
        t = action["type"]
        if t == "transfer":
            store.transfer(action["src"], action["dst"], int(action["amount"]))
        elif t == "corruption":
            store.set_balance(action["target"], int(action["amount"]))
        elif t == "summary_corruption":
            # corrupt summary index without touching ledger
            state = store.get_state()
            total = int(state.get("summary_total", 0))
            factor = int(action.get("factor", 2))
            store.set_summary_total(total * factor)
        else:
            raise ValueError(f"Unknown action type: {t}")

    def run_workload(
        self,
        initial_state: Dict[str, Any],
        profile: WorkloadProfile,
    ) -> Tuple[Dict[str, Any], BaselineRunInfo]:
        store = InMemoryStore(initial_state)
        agent = WorkloadAgent(seed=self.seed)
        actions = agent.generate_actions(profile)

        for action in actions:
            self._apply_action(store, action)

        info = BaselineRunInfo(steps_executed=len(actions))
        return store.get_state(), info
