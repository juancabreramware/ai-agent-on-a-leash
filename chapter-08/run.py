import json
import os
import platform
import uuid
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
from chapter_08_transactional_execution.transaction_manager import (
    TransactionManager,
)
from chapter_08_transactional_execution.recovery import RecoveryCoordinator


EXPERIMENT_ID = "exp-08-transactional-execution-reversible-actions-v1"
CHAPTER_NUMBER = 8


def _ensure_evidence_dir() -> Path:
    root = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_environment_info() -> dict:
    return {
        "os": platform.system(),
        "python": platform.python_version(),
    }


def _run_workload_1(tmpdir: Path):
    """Workload 1: deterministic failure at payment step.

    Returns list of run dicts for evidence file.
    """
    runs = []

    # Shared configuration
    ledger_path = tmpdir / "ledger.json"
    log_path = tmpdir / "transactions.log"

    # --- Baseline ---
    baseline_store = InMemoryOrderStore()
    baseline_file_tool = FileTool(ledger_path)
    baseline_agent = BaselineAgent(baseline_store, baseline_file_tool)

    baseline_store.clear()
    if ledger_path.exists():
        ledger_path.unlink()

    try:
        baseline_agent.run_workflow(
            order_id="order-1",
            amount=10.0,
            failure_point=FailurePoint.AFTER_LEDGER_AND_ORDER,
        )
        success = True
    except Exception:
        success = False

    # Measure partial_side_effects_count
    partial_count = 0
    orders = list(baseline_store.orders.keys())
    ledger_entries = baseline_file_tool.read_all()
    if orders or ledger_entries:
        partial_count = 1

    runs.append(
        {
            "variant": "baseline",
            "workload_id": "workload-1-partial-write-failure-baseline-vs-transactional",
            "run_id": f"baseline-{uuid.uuid4()}",
            "success": success,
            "metrics": {
                "partial_side_effects_count": float(partial_count),
                # No log for baseline, but include metric with 0 to preserve schema
                "log_entries_per_transaction": 0.0,
            },
        }
    )

    # --- Treatment ---
    tx_store = InMemoryOrderStore()
    tx_file_tool = FileTool(ledger_path)
    transactional_store = TransactionalOrderStore(tx_store)
    transactional_file = TransactionalFileTool(tx_file_tool)

    manager = TransactionManager(log_path)
    tx_agent = TransactionalAgent(manager, transactional_store, transactional_file)

    tx_store.clear()
    if ledger_path.exists():
        ledger_path.unlink()
    if log_path.exists():
        log_path.unlink()

    try:
        tx_agent.run_workflow(
            transaction_id="tx-1",
            order_id="order-1",
            amount=10.0,
            failure_point=FailurePoint.AFTER_LEDGER_AND_ORDER,
        )
        tx_success = True
    except Exception:
        tx_success = False

    tx_orders = list(tx_store.orders.keys())
    tx_ledger_entries = tx_file_tool.read_all()
    if tx_orders or tx_ledger_entries:
        tx_partial = 1
    else:
        tx_partial = 0

    # Measure log entries from the manager
    log_entries_per_tx = float(len(manager.read_log_for_transaction("tx-1")))

    runs.append(
        {
            "variant": "treatment",
            "workload_id": "workload-1-partial-write-failure-baseline-vs-transactional",
            "run_id": f"treatment-{uuid.uuid4()}",
            "success": tx_success,
            "metrics": {
                "partial_side_effects_count": float(tx_partial),
                "log_entries_per_transaction": log_entries_per_tx,
            },
        }
    )

    return runs


def _run_workload_2(tmpdir: Path):
    """Workload 2: randomized failure points (small N for runtime bounds)."""
    import random

    runs = []
    N = 5  # bounded for sandbox
    random.seed(12345)

    ledger_path = tmpdir / "ledger.json"
    log_path = tmpdir / "transactions.log"

    failure_points = [
        FailurePoint.AFTER_ORDER_CREATE,
        FailurePoint.AFTER_LEDGER_AND_ORDER,
        FailurePoint.PAYMENT,
    ]

    # We only record aggregate metrics per variant for this workload
    baseline_partials = 0
    treatment_partials = 0

    # Baseline aggregate
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

        orders = list(store.orders.keys())
        ledger_entries = tool.read_all()
        if orders or ledger_entries:
            baseline_partials += 1

    runs.append(
        {
            "variant": "baseline",
            "workload_id": "workload-2-randomized-failure-points",
            "run_id": f"baseline-{uuid.uuid4()}",
            "success": True,
            "metrics": {
                "partial_side_effects_count": float(baseline_partials),
                "log_entries_per_transaction": 0.0,
            },
        }
    )

    # Treatment aggregate
    random.seed(12345)
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

        orders = list(store.orders.keys())
        ledger_entries = base_file.read_all()
        if orders or ledger_entries:
            treatment_partials += 1

    runs.append(
        {
            "variant": "treatment",
            "workload_id": "workload-2-randomized-failure-points",
            "run_id": f"treatment-{uuid.uuid4()}",
            "success": True,
            "metrics": {
                "partial_side_effects_count": float(treatment_partials),
                # We don't aggregate log count here; use 0 to maintain numeric metric
                "log_entries_per_transaction": 0.0,
            },
        }
    )

    return runs


def _run_workload_3(tmpdir: Path):
    """Workload 3: simulate crash and recovery using persisted log.

    In this offline script we approximate a crash by:
    - running the transactional workflow until just before rollback,
    - not calling commit/rollback,
    - constructing a new RecoveryCoordinator which uses the persisted log
      to roll back.
    """

    runs = []
    ledger_path = tmpdir / "ledger.json"
    log_path = tmpdir / "transactions.log"

    # Baseline: no automated recovery
    baseline_store = InMemoryOrderStore()
    baseline_tool = FileTool(ledger_path)
    baseline_agent = BaselineAgent(baseline_store, baseline_tool)

    baseline_store.clear()

    if ledger_path.exists():
        ledger_path.unlink()

    try:
        baseline_agent.run_workflow(
            order_id="order-crash",
            amount=99.0,
            failure_point=FailurePoint.AFTER_LEDGER_AND_ORDER,
        )
    except Exception:
        pass

    orders_after = list(baseline_store.orders.keys())
    ledger_after = baseline_tool.read_all()
    partial = 1 if (orders_after or ledger_after) else 0

    runs.append(
        {
            "variant": "baseline",
            "workload_id": "workload-3-recovery-from-crash-using-persisted-log",
            "run_id": f"baseline-{uuid.uuid4()}",
            "success": True,
            "metrics": {
                "partial_side_effects_count": float(partial),
                "log_entries_per_transaction": 0.0,
            },
        }
    )

    # Treatment: transactional with crash simulation and recovery
    store = InMemoryOrderStore()
    base_file = FileTool(ledger_path)
    t_store = TransactionalOrderStore(store)
    t_file = TransactionalFileTool(base_file)

    if ledger_path.exists():
        ledger_path.unlink()
    if log_path.exists():
        log_path.unlink()

    manager = TransactionManager(log_path)

    # Begin transaction and perform actions manually to simulate crash
    tx_id = "tx-crash"
    manager.begin(tx_id)

    def do_create():
        return t_store.create_order("order-crash", 99.0)

    def undo_create(result):
        t_store.delete_order(result["order_id"])

    manager.do_action(tx_id, "create_order", {"order_id": "order-crash", "amount": 99.0}, do_create, undo_create)

    def do_append():
        return t_file.append_entry({"order_id": "order-crash", "amount": 99.0})

    def undo_append(_):
        t_file.truncate_to_size(0)

    manager.do_action(tx_id, "append_ledger", {"order_id": "order-crash", "amount": 99.0}, do_append, undo_append)

    # Simulated crash: we do not call commit or rollback here.

    # On "restart": new RecoveryCoordinator uses the same manager/log
    coordinator = RecoveryCoordinator()
    compensation_failures = coordinator.recover_incomplete_transactions(log_path, {"create_order": undo_create, "append_ledger": undo_append})

    orders_final = list(store.orders.keys())
    ledger_final = base_file.read_all()
    partial_after_recovery = 1 if (orders_final or ledger_final) else 0
    log_entries_per_tx = float(len(manager.read_log_for_transaction(tx_id)))

    runs.append(
        {
            "variant": "treatment",
            "workload_id": "workload-3-recovery-from-crash-using-persisted-log",
            "run_id": f"treatment-{uuid.uuid4()}",
            "success": compensation_failures == 0 and partial_after_recovery == 0,
            "metrics": {
                "partial_side_effects_count": float(partial_after_recovery),
                "log_entries_per_transaction": log_entries_per_tx,
            },
        }
    )

    return runs


def main() -> None:
    evidence_dir = _ensure_evidence_dir()
    tmp_root = Path("/tmp") / "chapter_08_transactional_execution_run"
    tmp_root.mkdir(parents=True, exist_ok=True)

    runs = []
    runs.extend(_run_workload_1(tmp_root / "w1"))
    runs.extend(_run_workload_2(tmp_root / "w2"))
    runs.extend(_run_workload_3(tmp_root / "w3"))

    results = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": _make_environment_info(),
        "runs": runs,
        "notes": "Evidence generated by run.py for baseline vs transactional transactional-execution experiment.",
    }

    out_path = evidence_dir / "results.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
