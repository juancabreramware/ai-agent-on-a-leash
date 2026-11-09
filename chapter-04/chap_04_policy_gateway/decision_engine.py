from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .policies import Policy, PolicyResult, build_policy_store


@dataclass
class Decision:
    effect: str  # allow | deny
    policy_id: str
    policy_effect: str  # underlying policy effect
    reason: str
    latency_ms: float


class DecisionEngine:
    """Applies a set of policies to an action context deterministically."""

    def __init__(self, policies: List[Policy] | None = None) -> None:
        self.policies: List[Policy] = policies if policies is not None else build_policy_store()

    def decide(self, ctx: Dict[str, Any]) -> Decision:
        start = time.perf_counter()
        # Compose policy results. For this experiment we use a deny-overrides
        # strategy: any deny wins; otherwise allow if at least one allow, else
        # not_applicable -> allow (no policy matched).
        final_effect = "allow"
        final_policy_id = "policy_none_matched"
        final_policy_effect = "not_applicable"
        final_reason = "No applicable policies; default allow."

        for policy in self.policies:
            result: PolicyResult = policy.evaluate(ctx)
            if result.effect == "deny":
                final_effect = "deny"
                final_policy_id = result.policy_id
                final_policy_effect = result.effect
                final_reason = result.reason
                break
            if result.effect == "allow" and final_effect != "deny":
                # Prefer a concrete allow over not_applicable
                final_effect = "allow"
                final_policy_id = result.policy_id
                final_policy_effect = result.effect
                final_reason = result.reason

        latency_ms = (time.perf_counter() - start) * 1000.0
        return Decision(
            effect=final_effect,
            policy_id=final_policy_id,
            policy_effect=final_policy_effect,
            reason=final_reason,
            latency_ms=latency_ms,
        )
