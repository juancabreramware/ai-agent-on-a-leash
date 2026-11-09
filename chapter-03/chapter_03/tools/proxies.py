from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Tuple

from chapter_03.environment import EnvironmentState
from chapter_03.capabilities.model import (
    Capability,
    ReadFileScope,
    WriteFileScope,
    TransferFundsScope,
    ListUsersScope,
)
from . import protected_tools


@dataclass
class ProxyMetrics:
    unauthorized_actions_executed: float = 0.0
    unauthorized_actions_blocked: float = 0.0
    authorized_actions_executed: float = 0.0
    secrets_exposed_to_agent: float = 0.0


@dataclass
class ToolProxyLayer:
    state: EnvironmentState
    metrics: ProxyMetrics = field(default_factory=ProxyMetrics)

    # Helper checks

    def _path_in_prefixes(self, path: str, prefixes: list[str]) -> bool:
        normalized = path
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return True
        return False

    # Capability-enforcing operations

    def invoke_read_file(self, cap: Capability, path: str) -> Tuple[bool, str | None, str | None]:
        assert isinstance(cap.scope, ReadFileScope)
        if not self._path_in_prefixes(path, cap.scope.allowed_prefixes):
            self.metrics.unauthorized_actions_blocked += 1.0
            return False, None, "path_not_in_scope"
        content = protected_tools.read_file(path)
        self.metrics.authorized_actions_executed += 1.0
        # Secrets exposure is tracked by workloads based on returned content
        return True, content, None

    def invoke_write_file(self, cap: Capability, path: str, content: str) -> Tuple[bool, None, str | None]:
        assert isinstance(cap.scope, WriteFileScope)
        if not self._path_in_prefixes(path, cap.scope.allowed_prefixes):
            self.metrics.unauthorized_actions_blocked += 1.0
            return False, None, "path_not_in_scope"
        protected_tools.write_file(path, content)
        self.metrics.authorized_actions_executed += 1.0
        return True, None, None

    def invoke_transfer_funds(
        self,
        cap: Capability,
        from_account: str,
        to_account: str,
        amount: float,
        currency: str,
    ) -> Tuple[bool, bool | None, str | None]:
        assert isinstance(cap.scope, TransferFundsScope)
        scope: TransferFundsScope = cap.scope
        if from_account not in scope.from_accounts or to_account not in scope.to_accounts:
            self.metrics.unauthorized_actions_blocked += 1.0
            return False, None, "account_not_in_scope"
        if amount > scope.max_amount_per_call:
            self.metrics.unauthorized_actions_blocked += 1.0
            return False, None, "amount_exceeds_limit"
        if currency != scope.allowed_currency:
            self.metrics.unauthorized_actions_blocked += 1.0
            return False, None, "currency_not_allowed"
        ok = protected_tools.transfer_funds(self.state, from_account, to_account, amount, currency)
        if ok:
            self.metrics.authorized_actions_executed += 1.0
        else:
            # Even if protected tool refuses for internal reasons, the call
            # was within capability scope and is treated as authorized.
            self.metrics.authorized_actions_executed += 1.0
        return True, ok, None

    def invoke_list_users(self, cap: Capability) -> Tuple[bool, list[str] | None, str | None]:
        assert isinstance(cap.scope, ListUsersScope)
        users = protected_tools.list_users(self.state)
        self.metrics.authorized_actions_executed += 1.0
        return True, users, None


def metrics_to_dict(m: ProxyMetrics) -> Dict[str, float]:
    return {
        "unauthorized_actions_executed": float(m.unauthorized_actions_executed),
        "unauthorized_actions_blocked": float(m.unauthorized_actions_blocked),
        "authorized_actions_executed": float(m.authorized_actions_executed),
        "secrets_exposed_to_agent": float(m.secrets_exposed_to_agent),
    }
