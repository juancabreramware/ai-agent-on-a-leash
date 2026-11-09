from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List


@dataclass
class ActionLogEntry:
    transaction_id: str
    sequence: int
    action_name: str
    params: Dict[str, Any]
    status: str  # "done" or "compensated"


class TransactionManager:
    """Simple application-level transaction manager with an append-only log.

    This manager:
    - Tracks an in-memory list of ActionLogEntry per transaction.
    - Persists entries to a JSON-lines log file for crash recovery.
    - Coordinates do/compensate operations.
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._entries: Dict[str, List[ActionLogEntry]] = {}

    def begin(self, transaction_id: str) -> None:
        self._entries[transaction_id] = []

    def _append_entry(self, entry: ActionLogEntry) -> None:
        self._entries.setdefault(entry.transaction_id, []).append(entry)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def do_action(
        self,
        transaction_id: str,
        action_name: str,
        params: Dict[str, Any],
        do_fn: Callable[[], Any],
        undo_fn: Callable[[Any], None],
    ) -> Any:
        """Execute do_fn and record a log entry for later compensation.

        The undo_fn itself is not serialized; recovery will look up a
        compensating function by action_name.
        """

        seq = len(self._entries.get(transaction_id, [])) + 1
        result = do_fn()
        entry = ActionLogEntry(
            transaction_id=transaction_id,
            sequence=seq,
            action_name=action_name,
            params=params,
            status="done",
        )
        self._append_entry(entry)
        return result

    def commit(self, transaction_id: str) -> None:
        # In this simple implementation, commit is a no-op; log remains.
        pass

    def rollback(self, transaction_id: str, compensators: Dict[str, Callable[[Dict[str, Any]], None]]) -> int:
        """Rollback by invoking compensating actions in reverse order.

        Returns the number of compensation failures.
        """
        failures = 0
        entries = list(self._entries.get(transaction_id, []))
        for entry in reversed(entries):
            if entry.status == "compensated":
                continue
            compensator = compensators.get(entry.action_name)
            if not compensator:
                continue
            try:
                compensator(entry.params)
                entry.status = "compensated"
                self._append_entry(entry)
            except Exception:
                failures += 1
        return failures

    def read_log_for_transaction(self, transaction_id: str) -> List[ActionLogEntry]:
        return list(self._entries.get(transaction_id, []))

    @staticmethod
    def parse_log_file(path: Path) -> List[ActionLogEntry]:
        entries: List[ActionLogEntry] = []
        if not path.exists():
            return entries
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    entries.append(
                        ActionLogEntry(
                            transaction_id=data["transaction_id"],
                            sequence=int(data["sequence"]),
                            action_name=str(data["action_name"]),
                            params=dict(data.get("params", {})),
                            status=str(data.get("status", "done")),
                        )
                    )
                except Exception:
                    continue
        return entries
