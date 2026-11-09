from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .model import (
    Capability,
    CapabilityType,
    Principal,
    ReadFileScope,
    WriteFileScope,
    TransferFundsScope,
    ListUsersScope,
)
from .registry import CapabilityRegistry
from chapter_03.environment import (
    REPORTS_DIR,
    KB_DIR,
    LOGS_DIR,
    PUBLIC_DIR,
)


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    capability: Capability | None = None


class PolicyEngine:
    """Deterministic policy engine for granting capabilities.

    Rules are intentionally simple but expressive enough for the workloads.
    """

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def bootstrap_principal(self, principal: Principal) -> List[Capability]:
        """Grant initial capabilities for a principal based on its id."""
        caps: List[Capability] = []
        pid = principal.principal_id
        if pid == "reporting_bot":
            caps.append(self._make_read_file_cap(pid, "cap_reports_read", [REPORTS_DIR + "/"]))
            caps.append(self._make_list_users_cap(pid, "cap_list_users_read"))
        elif pid == "junior_support_bot":
            caps.append(self._make_read_file_cap(pid, "cap_kb_read", [KB_DIR + "/"]))
            caps.append(
                self._make_transfer_cap(
                    pid,
                    "cap_small_transfers",
                    from_accounts=["ops"],
                    to_accounts=["customer_x", "customer_y"],
                    max_amount_per_call=100.0,
                    currency="USD",
                )
            )
        elif pid == "analysis_bot":
            caps.append(self._make_read_file_cap(pid, "cap_logs_read", [LOGS_DIR + "/"]))
        elif pid == "public_summary_bot":
            caps.append(self._make_read_file_cap(pid, "cap_public_read", [PUBLIC_DIR + "/"]))
        for c in caps:
            self.registry.add_capability(c)
        return caps

    def request_capability(
        self,
        principal: Principal,
        type_: CapabilityType,
        **kwargs,
    ) -> PolicyDecision:
        """Handle explicit capability escalation requests.

        For this experiment, only `analysis_bot` may request additional
        read_file scopes on logs. All other requests are denied.
        """
        pid = principal.principal_id
        if type_ == "read_file" and pid == "analysis_bot":
            prefixes: List[str] = kwargs.get("allowed_prefixes", [])
            # Only allow more log directory prefixes under LOGS_DIR
            safe_prefixes: List[str] = []
            for p in prefixes:
                if p.startswith(LOGS_DIR + "/"):
                    safe_prefixes.append(p)
            if not safe_prefixes:
                return PolicyDecision(False, "requested_prefix_out_of_logs_scope")
            cap_id = f"cap_logs_read_extra_{len(self.registry._caps_by_id)}"
            cap = self._make_read_file_cap(pid, cap_id, safe_prefixes)
            self.registry.add_capability(cap)
            return PolicyDecision(True, "granted_additional_logs_read", cap)

        # Deny all other escalation types for all principals
        return PolicyDecision(False, "capability_type_or_principal_not_allowed_for_escalation")

    # Internal helpers

    def _make_read_file_cap(self, principal_id: str, cap_id: str, prefixes: List[str]) -> Capability:
        return Capability(
            capability_id=cap_id,
            principal_id=principal_id,
            type="read_file",
            scope=ReadFileScope(allowed_prefixes=prefixes),
        )

    def _make_write_file_cap(self, principal_id: str, cap_id: str, prefixes: List[str]) -> Capability:
        return Capability(
            capability_id=cap_id,
            principal_id=principal_id,
            type="write_file",
            scope=WriteFileScope(allowed_prefixes=prefixes),
        )

    def _make_transfer_cap(
        self,
        principal_id: str,
        cap_id: str,
        from_accounts: List[str],
        to_accounts: List[str],
        max_amount_per_call: float,
        currency: str,
    ) -> Capability:
        return Capability(
            capability_id=cap_id,
            principal_id=principal_id,
            type="transfer_funds",
            scope=TransferFundsScope(
                from_accounts=list(from_accounts),
                to_accounts=list(to_accounts),
                max_amount_per_call=max_amount_per_call,
                allowed_currency=currency,
            ),
        )

    def _make_list_users_cap(self, principal_id: str, cap_id: str) -> Capability:
        return Capability(
            capability_id=cap_id,
            principal_id=principal_id,
            type="list_users",
            scope=ListUsersScope(read_only=True),
        )
