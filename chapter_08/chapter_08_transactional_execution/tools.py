from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


class InMemoryOrderStore:
    """Simple in-memory order store used by both baseline and transactional variants."""

    def __init__(self) -> None:
        self.orders: Dict[str, Dict[str, Any]] = {}

    def clear(self) -> None:
        self.orders.clear()

    def create(self, order_id: str, amount: float) -> Dict[str, Any]:
        order = {"order_id": order_id, "amount": amount}
        self.orders[order_id] = order
        return order

    def delete(self, order_id: str) -> None:
        self.orders.pop(order_id, None)


class FileTool:
    """Baseline file tool for ledger operations (append-only JSON lines)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        items: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    # For robustness we ignore malformed lines in baseline tool.
                    continue
        return items


@dataclass
class TransactionalOrderStore:
    """Transactional wrapper for InMemoryOrderStore.

    It does not manage transactions itself; it just provides reversible
    operations that the TransactionManager can call.
    """

    underlying: InMemoryOrderStore

    def create_order(self, order_id: str, amount: float) -> Dict[str, Any]:
        return self.underlying.create(order_id, amount)

    def delete_order(self, order_id: str) -> None:
        self.underlying.delete(order_id)


@dataclass
class TransactionalFileTool:
    """Transactional wrapper around FileTool.

    Uses simple compensating actions:
    - append_entry: record added data; undo by truncating file to size 0 or
      another precomputed size.
    """

    underlying: FileTool

    def append_entry(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.underlying.append(record)
        return {"appended": True}

    def truncate_to_size(self, size: int) -> None:
        path = self.underlying.path
        if not path.exists():
            return
        with path.open("r+b") as f:
            f.truncate(size)
