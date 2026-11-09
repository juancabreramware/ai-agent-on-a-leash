import random
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


class RandomizedFailuresTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path("/tmp") / "chapter08_test_randomized"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def test_randomized_failure_points_rollback_success(self) -> None:
        ledger_path = self.tmpdir / "ledger.json"
        log_path = self.tmpdir / "transactions.log"

        failure_points = [
            FailurePoint.AFTER_ORDER_CREATE,
            FailurePoint.AFTER_LEDGER_AND_ORDER,
            FailurePoint.PAYMENT,
        ]

        N = 10

        # Baseline: expect some partial side effects
        random.seed(123)
        baseline_partial_count = 0
        for i in range(N):
            fp = random.choice(failure_points)
            store = InMemoryOrderStore()
            tool = FileTool(ledger_path)
            agent = BaselineAgent(store, tool)

            store.clear()
            if ledger_path.exists():
                ledger_path.unlink()

            try:
                agent.run_workflow(
                    order_id=f"order-{i}",
                    amount=10.0 + i,
                    failure_point=fp,
                )
            except Exception:
                pass

            if store.orders or tool.read_all():
                baseline_partial_count += 1

        self.assertGreater(
            baseline_partial_count,
            0,
            "Baseline should produce partial side effects under random failures.",
        )

        # Transactional: rollback should always restore pre-state
        random.seed(123)
        treatment_partial_count = 0
        for i in range(N):
            fp = random.choice(failure_points)
            store = InMemoryOrderStore()
            base_file = FileTool(ledger_path)
            t_store = TransactionalOrderStore(store)
            t_file = TransactionalFileTool(base_file)
            manager = TransactionManager(log_path)
            agent = TransactionalAgent(manager, t_store, t_file)

            store.clear()
            if ledger_path.exists():
                ledger_path.unlink()
            if log_path.exists():
                log_path.unlink()

            try:
                agent.run_workflow(
                    transaction_id=f"tx-{i}",
                    order_id=f"order-{i}",
                    amount=10.0 + i,
                    failure_point=fp,
                )
            except Exception:
                pass

            if store.orders or base_file.read_all():
                treatment_partial_count += 1

        self.assertEqual(
            treatment_partial_count,
            0,
            "Transactional rollback must restore pre-transaction state.",
        )


if __name__ == "__main__":
    unittest.main()
