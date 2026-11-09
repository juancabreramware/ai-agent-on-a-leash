from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from context_tokens import ContextToken
from policies import (
    AccessPolicy,
    PolicyDecision,
    SENSITIVITY_NORMAL,
    SENSITIVITY_PII,
    SENSITIVITY_SECRET,
    apply_redaction,
)


@dataclass
class ScopedMemoryItem:
    content: Dict[str, Any]
    scope: str
    tenant_id: str
    task_id: str
    role: str
    sensitivity: str = SENSITIVITY_NORMAL


@dataclass
class QueryResult:
    item: Dict[str, Any]
    sensitivity: str
    decision: PolicyDecision
    redacted: bool


class ScopedMemoryStore:
    """Treatment memory store enforcing scopes and redaction.

    Each item is tagged with:
    - tenant_id
    - task_id
    - scope (e.g. tenant:acme_corp:task1 or tenant:acme_corp:shared)
    - role (writer role; not used for access decisions in this toy
      implementation, but included for completeness)
    - sensitivity level

    Reads require a ContextToken and are filtered strictly by scopes.
    """

    def __init__(self) -> None:
        self._items: List[ScopedMemoryItem] = []

    def write(
        self,
        ctx: ContextToken,
        content: Dict[str, Any],
        sensitivity: str = SENSITIVITY_NORMAL,
        scope: Optional[str] = None,
    ) -> None:
        if ctx is None:
            raise ValueError("ContextToken is required for write")
        if sensitivity not in {SENSITIVITY_NORMAL, SENSITIVITY_PII, SENSITIVITY_SECRET}:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
        item_scope = scope or f"tenant:{ctx.tenant_id}:{ctx.task_id}"
        self._items.append(
            ScopedMemoryItem(
                content=dict(content),
                scope=item_scope,
                tenant_id=ctx.tenant_id,
                task_id=ctx.task_id,
                role=ctx.role,
                sensitivity=sensitivity,
            )
        )

    def _match_query(self, item: ScopedMemoryItem, query: Dict[str, Any]) -> bool:
        for k, v in query.items():
            if item.content.get(k) != v:
                return False
        return True

    def query(self, ctx: ContextToken, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        if ctx is None:
            raise ValueError("ContextToken is required for query")
        results: List[Dict[str, Any]] = []
        for item in self._items:
            decision = AccessPolicy.can_access_scope(ctx, item.scope)
            if not decision.allowed:
                continue
            if not self._match_query(item, query):
                continue
            results.append(dict(item.content))
        return results

    def query_redacted(self, ctx: ContextToken, query: Dict[str, Any]) -> List[QueryResult]:
        if ctx is None:
            raise ValueError("ContextToken is required for query_redacted")

        results: List[QueryResult] = []
        for item in self._items:
            decision = AccessPolicy.can_access_scope(ctx, item.scope)
            if not decision.allowed:
                continue
            if not self._match_query(item, query):
                continue

            # Determine which fields might be sensitive.
            pii_fields = [k for k in item.content.keys() if k in {"email", "phone"}]
            secret_fields = [k for k in item.content.keys() if k in {"api_token", "secret", "card_last4"}]

            redacted_content, changed = apply_redaction(
                ctx,
                item.sensitivity,
                {k: str(v) if isinstance(v, (int, float)) else v for k, v in item.content.items()},
                pii_fields=pii_fields,
                secret_fields=secret_fields,
            )

            results.append(
                QueryResult(
                    item=redacted_content,
                    sensitivity=item.sensitivity,
                    decision=decision,
                    redacted=changed,
                )
            )

        return results


def measure_query_latency(store: ScopedMemoryStore, ctx: ContextToken, query: Dict[str, Any]) -> Tuple[float, int]:
    """Helper used in experiments to measure simple latency and count results.

    Returns (latency_ms, num_results).

    This helper is not wired into the current workloads, so
    `query_latency` is not reported in evidence metrics for this
    revision.
    """

    start = perf_counter()
    results = store.query(ctx, query)
    end = perf_counter()
    latency_ms = (end - start) * 1000.0
    return latency_ms, len(results)
