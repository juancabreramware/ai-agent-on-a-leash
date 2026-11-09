from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from chapter_03.environment import EnvironmentState
from chapter_03.capabilities.model import Capability, Principal
from chapter_03.capabilities.registry import CapabilityRegistry
from chapter_03.capabilities.policy_engine import PolicyEngine, PolicyDecision
from chapter_03.tools.proxies import ToolProxyLayer


@dataclass
class TreatmentAgent:
    principal: Principal
    registry: CapabilityRegistry
    policy_engine: PolicyEngine
    proxies: ToolProxyLayer

    def list_capabilities(self) -> List[Capability]:
        return self.registry.list_capabilities_for_principal(self.principal.principal_id)

    def request_capability(self, type_: str, **kwargs) -> PolicyDecision:
        return self.policy_engine.request_capability(self.principal, type_, **kwargs)

    # Helper methods to locate appropriate capability and call proxies

    def _find_capability(self, type_: str) -> Capability | None:
        for cap in self.list_capabilities():
            if cap.type == type_:
                return cap
        return None

    def safe_read_file(self, path: str) -> Tuple[bool, str | None, str | None]:
        cap = self._find_capability("read_file")
        if cap is None:
            return False, None, "no_read_file_capability"
        return self.proxies.invoke_read_file(cap, path)

    def safe_write_file(self, path: str, content: str) -> Tuple[bool, None, str | None]:
        cap = self._find_capability("write_file")
        if cap is None:
            return False, None, "no_write_file_capability"
        return self.proxies.invoke_write_file(cap, path, content)

    def safe_transfer_funds(self, from_account: str, to_account: str, amount: float, currency: str) -> Tuple[bool, bool | None, str | None]:
        cap = self._find_capability("transfer_funds")
        if cap is None:
            return False, None, "no_transfer_funds_capability"
        return self.proxies.invoke_transfer_funds(cap, from_account, to_account, amount, currency)

    def safe_list_users(self) -> Tuple[bool, List[str] | None, str | None]:
        cap = self._find_capability("list_users")
        if cap is None:
            return False, None, "no_list_users_capability"
        return self.proxies.invoke_list_users(cap)
