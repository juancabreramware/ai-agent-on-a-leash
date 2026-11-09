from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Set


@dataclass(frozen=True)
class ContextToken:
    """Represents the caller's identity and allowed scopes.

    - task_id: logical task/session identifier.
    - tenant_id: logical tenant or organization.
    - role: e.g. "agent", "auditor", "supervisor".
    - allowed_scopes: set of scope IDs that the caller may access.

    The treatment store requires a ContextToken for every operation and
    uses it to enforce isolation and apply redaction policies.
    """

    task_id: str
    tenant_id: str
    role: str
    allowed_scopes: FrozenSet[str] = field(default_factory=frozenset)

    @staticmethod
    def create(task_id: str, tenant_id: str, role: str, allowed_scopes: Set[str]) -> "ContextToken":
        return ContextToken(
            task_id=task_id,
            tenant_id=tenant_id,
            role=role,
            allowed_scopes=frozenset(allowed_scopes),
        )
