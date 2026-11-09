from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class PolicyResult:
    effect: str  # "allow" | "deny" | "not_applicable"
    policy_id: str
    reason: str


@dataclass
class Policy:
    policy_id: str
    description: str

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyResult:  # pragma: no cover - overridden
        raise NotImplementedError


class SpendLimitPolicy(Policy):
    def __init__(self, single_tx_limit: float, daily_limit: float) -> None:
        super().__init__(
            policy_id="policy_spend_limits",
            description="Enforce per-transaction and per-day spending limits.",
        )
        self.single_tx_limit = float(single_tx_limit)
        self.daily_limit = float(daily_limit)

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get("tool_name") != "submit_purchase_order":
            return PolicyResult("not_applicable", self.policy_id, "Not a purchase order")
        amount = float(ctx.get("amount", 0.0))
        current_spend_today = float(ctx.get("current_spend_today", 0.0))
        if amount > self.single_tx_limit:
            return PolicyResult(
                effect="deny",
                policy_id=self.policy_id,
                reason=f"Amount {amount} exceeds single-tx limit {self.single_tx_limit}",
            )
        if current_spend_today + amount > self.daily_limit:
            return PolicyResult(
                effect="deny",
                policy_id=self.policy_id,
                reason=(
                    f"Cumulative spend {current_spend_today + amount} exceeds "
                    f"daily limit {self.daily_limit}"
                ),
            )
        return PolicyResult("allow", self.policy_id, "Within spend limits")


class CustomerAccessPolicy(Policy):
    def __init__(self) -> None:
        super().__init__(
            policy_id="policy_customer_access",
            description="Account managers may access only their assigned customers.",
        )

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get("tool_name") != "get_customer_record":
            return PolicyResult("not_applicable", self.policy_id, "Not a customer access request")
        role = ctx.get("user_role")
        if role != "account_manager":
            return PolicyResult("deny", self.policy_id, "Only account managers may access customer records")
        requested = ctx.get("requested_customer_id")
        allowed = ctx.get("allowed_customer_ids") or []
        if requested in allowed:
            return PolicyResult("allow", self.policy_id, "Customer is in allowed list")
        return PolicyResult("deny", self.policy_id, f"Customer {requested} not in allowed list")


class DeploymentWindowPolicy(Policy):
    def __init__(self) -> None:
        super().__init__(
            policy_id="policy_deployment_window",
            description="Block risky production deployments outside business hours and during freeze windows.",
        )

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get("tool_name") != "deploy_configuration":
            return PolicyResult("not_applicable", self.policy_id, "Not a deployment request")
        env = ctx.get("environment")
        if env != "production":
            return PolicyResult("allow", self.policy_id, "Non-production deployment allowed")
        # For simplicity, treat any production deployment as denied outside business hours
        is_business_hours = bool(ctx.get("is_business_hours", False))
        if not is_business_hours:
            return PolicyResult("deny", self.policy_id, "Production deployment outside business hours")
        return PolicyResult("allow", self.policy_id, "Production deployment inside business hours")


class ExportScopePolicy(Policy):
    def __init__(self) -> None:
        super().__init__(
            policy_id="policy_export_scope",
            description="Disallow bulk export of all customer data by default.",
        )

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get("tool_name") != "export_customer_data":
            return PolicyResult("not_applicable", self.policy_id, "Not a data export request")
        scope = ctx.get("scope")
        if scope == "all_customers":
            return PolicyResult("deny", self.policy_id, "Bulk export of all customers is not allowed")
        return PolicyResult("allow", self.policy_id, "Export scope allowed")


def build_policy_store() -> List[Policy]:
    """Return the static list of policies used by the decision engine.

    Policies are evaluated in sequence; the engine composes them into a final
    decision. This set remains static within a single experiment run.
    """

    return [
        SpendLimitPolicy(single_tx_limit=10_000.0, daily_limit=10_000.0),
        CustomerAccessPolicy(),
        DeploymentWindowPolicy(),
        ExportScopePolicy(),
    ]
