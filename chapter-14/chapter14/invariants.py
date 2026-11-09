from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class InvariantResult:
    ok: bool
    errors: List[str]


class InvariantsEngine:
    """Shared invariants for ledger and summary index."""

    def check(self, state: Dict[str, Any]) -> InvariantResult:
        errors: List[str] = []
        accounts = state.get("accounts", {}) or {}
        # 1. Non-negative balances
        for acc, bal in accounts.items():
            if not isinstance(bal, int):
                errors.append(f"balance_not_int:{acc}")
            elif bal < 0:
                errors.append(f"negative_balance:{acc}")
        # 2. Total sum consistency
        total = sum(int(b or 0) for b in accounts.values())
        expected_total = state.get("summary_total")
        if expected_total is not None and int(expected_total) != total:
            errors.append("summary_mismatch")
        # 3. Required keys
        if "accounts" not in state:
            errors.append("missing_accounts")
        ok = not errors
        return InvariantResult(ok=ok, errors=errors)

    def count_violations(self, state: Dict[str, Any]) -> int:
        return len(self.check(state).errors)

    def describe_violations(self, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        res = self.check(state)
        return res.ok, list(res.errors)
