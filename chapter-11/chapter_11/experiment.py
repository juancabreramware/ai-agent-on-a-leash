from __future__ import annotations

from typing import Dict, List

from .baseline_agent import BaselineAgent
from .supervised_agent import SupervisedAgent
from .workloads import get_workloads
from .evaluator import compute_task_metrics


def run_full_experiment() -> List[Dict[str, object]]:
    """Run baseline and supervised variants across all workloads.

    Returns a list of per-workload run dicts ready for inclusion in the
    top-level evidence JSON under the "runs" field.
    """

    workloads = get_workloads()

    runs: List[Dict[str, object]] = []

    baseline_agent = BaselineAgent()
    supervised_agent = SupervisedAgent()

    for workload in workloads:
        workload_id = workload.id

        # Baseline run: plan per task and aggregate metrics by summation.
        baseline_metrics_agg = {
            "unsafe_actions_proposed": 0,
            "unsafe_actions_approved": 0,
            "actions_total_approved": 0,
        }
        baseline_success_overall = True

        for task in workload.tasks:
            actions = baseline_agent.plan(task.task_id, task.description)
            metrics, success = compute_task_metrics(proposed=actions, approved=actions)
            for k, v in metrics.items():
                baseline_metrics_agg[k] += int(v)
            baseline_success_overall = baseline_success_overall and success

        runs.append(
            {
                "variant": "baseline",
                "workload_id": workload_id,
                "run_id": f"{workload_id}-baseline-1",
                "success": bool(baseline_success_overall),
                "metrics": {k: float(v) for k, v in baseline_metrics_agg.items()},
            }
        )

        # Treatment (supervised) run.
        treatment_metrics_agg = {
            "unsafe_actions_proposed": 0,
            "unsafe_actions_approved": 0,
            "actions_total_approved": 0,
        }
        treatment_success_overall = True

        for task in workload.tasks:
            proposed = supervised_agent.primary.plan(task.task_id, task.description)
            approved, _reviews = supervised_agent.plan(task.task_id, task.description)
            metrics, success = compute_task_metrics(proposed=proposed, approved=approved)
            for k, v in metrics.items():
                treatment_metrics_agg[k] += int(v)
            treatment_success_overall = treatment_success_overall and success

        runs.append(
            {
                "variant": "treatment",
                "workload_id": workload_id,
                "run_id": f"{workload_id}-treatment-1",
                "success": bool(treatment_success_overall),
                "metrics": {k: float(v) for k, v in treatment_metrics_agg.items()},
            }
        )

    return runs
