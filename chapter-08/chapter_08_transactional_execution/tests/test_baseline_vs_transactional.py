import unittest
from pathlib import Path

from chapter_08_transactional_execution.transactional_agent import (
    BaselineAgent,
    TransactionalAgent,
    FailurePoint,
)
from chapter_08_transactional_execution.tools import (
    InMemoryOrderStore,
    FileTool,
    TransactionalOrderStore,
    TransactionalFileTool,
)
from chapter_08_transactional_execution.transaction_manager import TransactionManager


class BaselineVsTransactionalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path("/tmp") / "chapter08_test_baseline_vs_tx"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def test_partial_write_failure_vs_transactional_rollback(self) -> None:
        ledger_path = self.tmpdir / "ledger.json"
        log_path = self.tmpdir / "transactions.log"

        # Baseline run
        baseline_store = InMemoryOrderStore()
        baseline_tool = FileTool(ledger_path)
        baseline_agent = BaselineAgent(baseline_store, baseline_tool)

        baseline_store.clear()
        if ledger_path.exists():
            ledger_path.unlink()

        with self.assertRaises(Exception):
            baseline_agent.run_workflow(
                order_id="order-1",
                amount=10.0,
                failure_point=FailurePoint.AFTER_LEDGER_AND_ORDER,
            )

        baseline_orders = list(baseline_store.orders.keys())
        baseline_ledger = baseline_tool.read_all()
        self.assertTrue(
            baseline_orders or baseline_ledger,
            "Baseline should leave partial side effects.",
        )

        # Transactional run
        tx_store = InMemoryOrderStore()
        base_file = FileTool(ledger_path)
        t_store = TransactionalOrderStore(tx_store)
        t_file = TransactionalFileTool(base_file)
        manager = TransactionManager(log_path)
        tx_agent = TransactionalAgent(manager, t_store, t_file)

        tx_store.clear()
        if ledger_path.exists():
            ledger_path.unlink()
        if log_path.exists():
            log_path.unlink()

        with self.assertRaises(Exception):
            tx_agent.run_workflow(
                transaction_id="tx-1",
                order_id="order-1",
                amount=10.0,
                failure_point=FailurePoint.AFTER_LEDGER_AND_ORDER,
            )

        tx_orders = list(tx_store.orders.keys())
        tx_ledger = base_file.read_all()
        self.assertEqual(tx_orders, [])
        self.assertEqual(tx_ledger, [])

        log_entries = manager.read_log_for_transaction("tx-1")
        self.assertGreaterEqual(
            len(log_entries),
            1,
            "Transactional variant must log side-effecting operations.",
        )


if __name__ == "__main__":
    unittest.main()
