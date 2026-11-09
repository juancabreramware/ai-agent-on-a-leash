from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import Capability


@dataclass
class CapabilityRegistry:
    _caps_by_id: Dict[str, Capability] = field(default_factory=dict)
    _caps_by_principal: Dict[str, List[str]] = field(default_factory=dict)

    def add_capability(self, cap: Capability) -> None:
        self._caps_by_id[cap.capability_id] = cap
        self._caps_by_principal.setdefault(cap.principal_id, []).append(cap.capability_id)

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        return self._caps_by_id.get(capability_id)

    def list_capabilities_for_principal(self, principal_id: str) -> List[Capability]:
        ids = self._caps_by_principal.get(principal_id, [])
        return [self._caps_by_id[cid] for cid in ids if cid in self._caps_by_id]

    def clear(self) -> None:
        self._caps_by_id.clear()
        self._caps_by_principal.clear()
