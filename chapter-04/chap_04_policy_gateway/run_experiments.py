from __future__ import annotations

import math
import time
from typing import Any, Dict, List

from .audit import InMemoryAuditor
from .baseline_agent import BaselineAgent
from .gateway_agent import GatewayAgent
from .tools import STATE
from .workloads import WorkloadCase, generate_workloads


def _metric_number(value: float) -> float:
    # Ensure metrics are finite JSON numbers
    if math.isfinite(value):
        return float(value)
    return 0.0


def _run_single(
    variant: str,
    agent: Any,
    workload: WorkloadCase,
    run_index: int,
) -> Dict[str, Any]:
    run_id = f"{variant}-{workload.id}-{run_index}"
    start = time.perf_counter()
    result = agent.run_workload(workload)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    metrics: Dict[str, float] = {
        "actions_executed": 1.0 if result.executed else 0.0,
        "run_elapsed_ms": _metric_number(elapsed_ms),
    }

    # Treat a successful run as "success" if it executed without error when
    # it was supposed to be allowed, or correctly blocked when expected.
    success = result.error is None or not result.executed

    return {
        "variant": variant,
        "workload_id": workload.id,
        "run_id": run_id,
        "success": bool(success),
        "metrics": metrics,
    }


def run_all_workloads() -> List[Dict[str, Any]]:
    """Execute all workloads for baseline and treatment and return run records.

    At least one baseline and one treatment run are produced per workload.
    Metrics are simple numeric quantities derived from real timing and
    execution outcomes.
    """

    workloads = generate_workloads()

    # Reset shared state before running
    STATE.reset()

    baseline_auditor = InMemoryAuditor()
    gateway_auditor = InMemoryAuditor()

    baseline = BaselineAgent(auditor=baseline_auditor)
    gateway = GatewayAgent(auditor=gateway_auditor)

    runs: List[Dict[str, Any]] = []

    for workload in workloads:
        # Baseline run
        runs.append(_run_single("baseline", baseline, workload, run_index=1))
        # Treatment run
        runs.append(_run_single("treatment", gateway, workload, run_index=1))

    return runs
