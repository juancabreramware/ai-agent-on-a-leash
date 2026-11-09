from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from .tools import InMemoryOrderStore, FileTool, TransactionalOrderStore, TransactionalFileTool
from .transaction_manager import TransactionManager


class FailurePoint(Enum):
    NONE = auto()
    AFTER_ORDER_CREATE = auto()
    AFTER_LEDGER_AND_ORDER = auto()
    PAYMENT = auto()


class FixedFailureException(Exception):
    pass


@dataclass
class BaselineAgent:
    order_store: InMemoryOrderStore
    file_tool: FileTool

    def run_workflow(self, order_id: str, amount: float, failure_point: FailurePoint) -> None:
        # Step 1: create order in memory
        self.order_store.create(order_id, amount)
        if failure_point == FailurePoint.AFTER_ORDER_CREATE:
            raise FixedFailureException("Failure after order create")

        # Step 2: append ledger entry
        self.file_tool.append({"order_id": order_id, "amount": amount})
        if failure_point == FailurePoint.AFTER_LEDGER_AND_ORDER:
            raise FixedFailureException("Failure after ledger and order")

        # Step 3: payment (simulated)
        self._payment_step(order_id, amount, failure_point)

    def _payment_step(self, order_id: str, amount: float, failure_point: FailurePoint) -> None:
        if failure_point == FailurePoint.PAYMENT:
            raise FixedFailureException("Failure during payment")
        # In real system, payment logic would go here.


@dataclass
class TransactionalAgent:
    manager: TransactionManager
    order_store: TransactionalOrderStore
    file_tool: TransactionalFileTool

    def run_workflow(
        self,
        transaction_id: str,
        order_id: str,
        amount: float,
        failure_point: FailurePoint,
    ) -> None:
        self.manager.begin(transaction_id)

        def do_create() -> Any:
            return self.order_store.create_order(order_id, amount)

        def undo_create(_params: dict) -> None:
            self.order_store.delete_order(order_id)

        self.manager.do_action(
            transaction_id,
            "create_order",
            {"order_id": order_id, "amount": amount},
            do_create,
            undo_create,
        )

        if failure_point == FailurePoint.AFTER_ORDER_CREATE:
            self.manager.rollback(transaction_id, {"create_order": undo_create})
            raise FixedFailureException("Failure after order create (tx)")

        def do_append() -> Any:
            return self.file_tool.append_entry({"order_id": order_id, "amount": amount})

        def undo_append(_params: dict) -> None:
            # For simplicity in this example, we truncate the ledger file to 0
            # which is correct because tests use fresh temporary directories
            # per workflow.
            self.file_tool.truncate_to_size(0)

        self.manager.do_action(
            transaction_id,
            "append_ledger",
            {"order_id": order_id, "amount": amount},
            do_append,
            undo_append,
        )

        if failure_point == FailurePoint.AFTER_LEDGER_AND_ORDER:
            self.manager.rollback(
                transaction_id,
                {"create_order": undo_create, "append_ledger": undo_append},
            )
            raise FixedFailureException("Failure after ledger and order (tx)")

        if failure_point == FailurePoint.PAYMENT:
            self.manager.rollback(
                transaction_id,
                {"create_order": undo_create, "append_ledger": undo_append},
            )
            raise FixedFailureException("Failure during payment (tx)")

        # Payment success path
        self.manager.commit(transaction_id)
