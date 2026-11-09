import time
import uuid
from typing import Dict, Any, List

from tools import MockTools, MockLLM
from agent_freeform import FreeformAgent
from agent_fsm import FSMAgent
from workloads import get_all_variants, WorkloadVariant
from evaluation import compute_run_metrics


def run_experiment_once(
    condition: str,
    workload: WorkloadVariant,
    seed_offset: int = 0,
) -> Dict[str, Any]:
    """Run a single baseline or treatment episode on a variant.

    Returns a structure containing the agent log and metadata.
    """

    base_seed = 1234 + seed_offset
    tools = MockTools(seed=base_seed)
    llm = MockLLM(seed=base_seed)

    if condition == "baseline":
        agent = FreeformAgent(tools=tools, llm=llm, max_steps=10)
    else:
        agent = FSMAgent(tools=tools, llm=llm, max_steps=10)

    run_log = agent.run(workload.workload_id, workload.payload)
    run_log["condition"] = condition
    run_log["workload_id"] = workload.workload_id
    run_log["variant_id"] = workload.variant_id
    return run_log


def run_full_experiment(repetitions: int = 1) -> List[Dict[str, Any]]:
    """Run baseline and treatment for each workload/variant.

    Returns a flat list of per-run records with attached metrics.
    """

    variants = get_all_variants()
    results: List[Dict[str, Any]] = []

    for v in variants:
        for condition in ("baseline", "treatment"):
            for rep in range(repetitions):
                run_log = run_experiment_once(condition, v, seed_offset=rep)
                metrics = compute_run_metrics(run_log)

                # Build evidence record for this run
                rec: Dict[str, Any] = {
                    "variant": condition,
                    "workload_id": f"{v.workload_id}/{v.variant_id}",
                    "run_id": str(uuid.uuid4()),
                    "success": bool(run_log.get("completed", False)),
                    "metrics": metrics,
                    "raw": {
                        "condition": condition,
                        "workload_id": v.workload_id,
                        "variant_id": v.variant_id,
                        "history_len": len(run_log.get("history", [])),
                    },
                }
                results.append(rec)

    return results
