from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


class InMemoryStore:
    """Simple dict-backed key-value store with ledger semantics.

    Structure:
    - "accounts": dict[str, int]
    - "summary_total": int
    - metadata keys like "last_run_id", "status".
    """

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None) -> None:
        self._state: Dict[str, Any] = copy.deepcopy(initial_state or {})

    def get_state(self) -> Dict[str, Any]:
        return self._state

    def set_state(self, new_state: Dict[str, Any]) -> None:
        self._state = new_state

    # Ledger-specific helpers
    def get_balance(self, account: str) -> int:
        return int(self._state.setdefault("accounts", {}).get(account, 0))

    def set_balance(self, account: str, amount: int) -> None:
        self._state.setdefault("accounts", {})[account] = int(amount)

    def transfer(self, src: str, dst: str, amount: int) -> None:
        accounts = self._state.setdefault("accounts", {})
        accounts[src] = int(accounts.get(src, 0)) - int(amount)
        accounts[dst] = int(accounts.get(dst, 0)) + int(amount)

    def set_summary_total(self, total: int) -> None:
        self._state["summary_total"] = int(total)

    def get_summary_total(self) -> int:
        return int(self._state.get("summary_total", 0))


@dataclass
class Snapshot:
    snapshot_id: str
    state: Dict[str, Any]
    digest: str
    metadata: Dict[str, Any]


class VersionedStore:
    """Decorator around InMemoryStore providing snapshots and integrity hashes."""

    def __init__(self, base_store: InMemoryStore) -> None:
        self._base = base_store
        self._snapshots: Dict[str, Snapshot] = {}
        self._counter = 0

    @staticmethod
    def _compute_digest(state: Dict[str, Any]) -> str:
        payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def create_snapshot(self, reason: str, run_id: str, step_id: int) -> Snapshot:
        self._counter += 1
        sid = f"ckpt-{self._counter}"
        state_copy = copy.deepcopy(self._base.get_state())
        digest = self._compute_digest(state_copy)
        meta = {"reason": reason, "run_id": run_id, "step_id": step_id}
        snap = Snapshot(snapshot_id=sid, state=state_copy, digest=digest, metadata=meta)
        self._snapshots[sid] = snap
        return snap

    def verify_snapshot(self, snapshot_id: str) -> bool:
        snap = self._snapshots[snapshot_id]
        current_digest = self._compute_digest(snap.state)
        return current_digest == snap.digest

    def restore_snapshot(self, snapshot_id: str) -> None:
        snap = self._snapshots[snapshot_id]
        self._base.set_state(copy.deepcopy(snap.state))

    def latest_snapshot_id(self) -> Optional[str]:
        if not self._snapshots:
            return None
        # snapshots are created with monotonically increasing counter
        return f"ckpt-{self._counter}"

    def get_state(self) -> Dict[str, Any]:
        return self._base.get_state()

    def set_state(self, new_state: Dict[str, Any]) -> None:
        self._base.set_state(new_state)

    # ledger helpers delegate to base
    def get_balance(self, account: str) -> int:
        return self._base.get_balance(account)

    def set_balance(self, account: str, amount: int) -> None:
        self._base.set_balance(account, amount)

    def transfer(self, src: str, dst: str, amount: int) -> None:
        self._base.transfer(src, dst, amount)

    def set_summary_total(self, total: int) -> None:
        self._base.set_summary_total(total)

    def get_summary_total(self) -> int:
        return self._base.get_summary_total()
