from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict

from .transaction_manager import TransactionManager


class RecoveryCoordinator:
    """Coordinator that uses persisted logs to recover incomplete transactions.

    It assumes transactions are incomplete if their last entry has status
    other than "compensated" and no explicit commit record exists.
    """

    def recover_incomplete_transactions(
        self,
        log_path: Path,
        compensators: Dict[str, Callable[[dict], None]],
    ) -> int:
        """Recover by applying compensating actions for each incomplete tx.

        Returns the total number of compensation failures.
        """
        entries = TransactionManager.parse_log_file(log_path)
        by_tx: Dict[str, list] = defaultdict(list)
        for e in entries:
            by_tx[e.transaction_id].append(e)

        failures = 0
        for tx_id, tx_entries in by_tx.items():
            # Decide whether transaction is incomplete: no explicit commit
            # marker is used, so we attempt to compensate if any entry has
            # status "done".
            has_uncompensated = any(e.status == "done" for e in tx_entries)
            if not has_uncompensated:
                continue
            # Apply compensations in reverse order
            for entry in sorted(tx_entries, key=lambda e: e.sequence, reverse=True):
                if entry.status == "compensated":
                    continue
                compensator = compensators.get(entry.action_name)
                if not compensator:
                    continue
                try:
                    compensator(entry.params)
                    entry.status = "compensated"
                except Exception:
                    failures += 1
        return failures
