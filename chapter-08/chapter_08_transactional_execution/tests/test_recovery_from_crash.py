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


class RecoveryFromCrashTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path("/tmp") / "chapter08_test_recovery"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def test_recovery_via_persisted_log(self) -> None:
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
        tx_id = "tx-crash-test"
        manager.begin(tx_id)

        def do_create():
            return t_store.create_order("order-crash", 99.0)

        def undo_create(params):  # params not used in this simple compensator
            t_store.delete_order("order-crash")

        manager.do_action(tx_id, "create_order", {"order_id": "order-crash", "amount": 99.0}, do_create, undo_create)

        def do_append():
            return t_file.append_entry({"order_id": "order-crash", "amount": 99.0})

        def undo_append(params):  # params not used
            t_file.truncate_to_size(0)

        manager.do_action(tx_id, "append_ledger", {"order_id": "order-crash", "amount": 99.0}, do_append, undo_append)

        # Simulated crash: no commit/rollback
        self.assertTrue(store.orders)
        self.assertTrue(base_file.read_all())

        coordinator = RecoveryCoordinator()
        failures = coordinator.recover_incomplete_transactions(log_path, {"create_order": undo_create, "append_ledger": undo_append})

        self.assertEqual(failures, 0)
        self.assertEqual(store.orders, {})
        self.assertEqual(base_file.read_all(), [])


if __name__ == "__main__":
    unittest.main()
