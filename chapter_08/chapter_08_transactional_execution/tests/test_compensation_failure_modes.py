import json
import unittest
from pathlib import Path

from chapter_08_transactional_execution.tools import (
    InMemoryOrderStore,
    FileTool,
    TransactionalOrderStore,
    TransactionalFileTool,
)
from chapter_08_transactional_execution.transaction_manager import TransactionManager
from chapter_08_transactional_execution.recovery import RecoveryCoordinator


class CompensationFailureModesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path("/tmp") / "chapter08_test_compensation_failure"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def test_compensator_handles_missing_resources_idempotently(self) -> None:
        ledger_path = self.tmpdir / "ledger.json"
        log_path = self.tmpdir / "transactions.log"

        store = InMemoryOrderStore()
        base_file = FileTool(ledger_path)
        t_store = TransactionalOrderStore(store)
        t_file = TransactionalFileTool(base_file)

        if ledger_path.exists():
            ledger_path.unlink()
        if log_path.exists():
            log_path.unlink()

        manager = TransactionManager(log_path)
        tx_id = "tx-idempotent"
        manager.begin(tx_id)

        def do_create():
            return t_store.create_order("order-x", 1.0)

        def undo_create(params):  # safe even if order already deleted
            t_store.delete_order(params["order_id"])

        manager.do_action(tx_id, "create_order", {"order_id": "order-x"}, do_create, undo_create)

        # Manually delete order before rollback
        store.orders.pop("order-x", None)

        failures = manager.rollback(tx_id, {"create_order": undo_create})
        self.assertEqual(failures, 0)
        self.assertEqual(store.orders, {})

    def test_log_corruption_is_ignored_by_recovery(self) -> None:
        ledger_path = self.tmpdir / "ledger2.json"
        log_path = self.tmpdir / "transactions_corrupt.log"

        # Write some malformed JSON to the log
        with log_path.open("w", encoding="utf-8") as f:
            f.write("not-json\n")
            f.write(json.dumps({"transaction_id": "tx", "sequence": 1, "action_name": "no_op", "params": {}, "status": "done"}) + "\n")

        coordinator = RecoveryCoordinator()

        def no_op_compensator(params):
            # Should be called at most once; any parse error lines are ignored.
            return None

        failures = coordinator.recover_incomplete_transactions(log_path, {"no_op": no_op_compensator})
        self.assertEqual(failures, 0)


if __name__ == "__main__":
    unittest.main()
