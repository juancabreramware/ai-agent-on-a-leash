from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List


Action = Dict[str, Any]


@dataclass
class WorkloadProfile:
    name: str
    num_actions: int
    pattern: str
    has_corruption: bool


def make_initial_state_fixture() -> Dict[str, Any]:
    # Simple deterministic initial ledger
    accounts = {"A": 1000, "B": 1000, "C": 1000}
    total = sum(accounts.values())
    return {
        "accounts": accounts,
        "summary_total": total,
        "status": "ready",
        "last_run_id": None,
    }


def get_workload_profiles() -> Dict[str, WorkloadProfile]:
    return {
        "WL1_nominal_no_corruption": WorkloadProfile(
            name="WL1_nominal_no_corruption",
            num_actions=20,
            pattern="nominal",
            has_corruption=False,
        ),
        "WL2_immediate_corruption_after_safe_start": WorkloadProfile(
            name="WL2_immediate_corruption_after_safe_start",
            num_actions=10,
            pattern="early_corruption",
            has_corruption=True,
        ),
        "WL3_late_corruption_after_long_run": WorkloadProfile(
            name="WL3_late_corruption_after_long_run",
            num_actions=100,
            pattern="late_corruption",
            has_corruption=True,
        ),
        "WL4_hidden_side_effect_external_view": WorkloadProfile(
            name="WL4_hidden_side_effect_external_view",
            num_actions=30,
            pattern="summary_divergence",
            has_corruption=True,
        ),
    }


class WorkloadAgent:
    """Deterministic agent generating actions based on a workload profile.

    Both baseline and treatment use this shared logic.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def generate_actions(self, profile: WorkloadProfile) -> List[Action]:
        if profile.pattern == "nominal":
            return self._gen_nominal(profile.num_actions)
        if profile.pattern == "early_corruption":
            return self._gen_early_corruption(profile.num_actions)
        if profile.pattern == "late_corruption":
            return self._gen_late_corruption(profile.num_actions)
        if profile.pattern == "summary_divergence":
            return self._gen_summary_divergence(profile.num_actions)
        raise ValueError(f"Unknown pattern: {profile.pattern}")

    def _random_account_pair(self) -> (str, str):
        accounts = ["A", "B", "C"]
        src, dst = self._rng.sample(accounts, 2)
        return src, dst

    def _gen_nominal(self, n: int) -> List[Action]:
        actions: List[Action] = []
        for _ in range(n):
            src, dst = self._random_account_pair()
            amount = self._rng.randint(1, 50)
            actions.append({"type": "transfer", "src": src, "dst": dst, "amount": amount})
        return actions

    def _gen_early_corruption(self, n: int) -> List[Action]:
        actions = self._gen_nominal(n)
        if n >= 4:
            # fourth action is corruption: set A to negative
            actions[3] = {"type": "corruption", "target": "A", "amount": -1000}
        return actions

    def _gen_late_corruption(self, n: int) -> List[Action]:
        actions = self._gen_nominal(n)
        if n >= 81:
            # corrupt around position 80: zero out rarely read account C
            idx = 80
            if idx < n:
                actions[idx] = {"type": "corruption", "target": "C", "amount": 0}
        return actions

    def _gen_summary_divergence(self, n: int) -> List[Action]:
        actions: List[Action] = []
        # first half: nominal transfers
        half = max(1, n // 2)
        actions.extend(self._gen_nominal(half))
        # insert divergence: wrong summary
        actions.append({"type": "summary_corruption", "factor": 2})
        # remaining actions: more nominal traffic
        remaining = max(0, n - len(actions))
        actions.extend(self._gen_nominal(remaining))
        return actions
