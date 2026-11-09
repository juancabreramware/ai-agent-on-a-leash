from __future__ import annotations

"""Entrypoint used by the book's evidence harness.

It must write `/evidence/results.json` (where `/evidence` is provided via the
`BOOKMAS_EVIDENCE_DIR` environment variable) with this exact structure:

{
  "chapter": 6,
  "experiment_id": "exp-06-bounded-loops-budgets-rate-limits-v1",
  "environment": {"os": <string>, "python": <string>},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": <string>,
      "run_id": <string>,
      "success": <bool>,
      "metrics": {"metric_name": <number>, ...}
    },
    ...
  ],
  "notes": <optional string>
}

At least one baseline and one treatment run are recorded per workload.
All values inside `metrics` are numeric (no strings/booleans/objects/nulls).
"""

import json
import os
import platform
import random
import sys
from typing import Any, Dict, List

from baseline_unbounded_agent import run_unbounded
from bounded_orchestrator import BudgetedOrchestrator
from workloads import make_workloads
from results_utils import make_run_id


EXPERIMENT_ID = "exp-06-bounded-loops-budgets-rate-limits-v1"
CHAPTER_NUMBER = 6


def run_experiment_suite() -> Dict[str, Any]:
    # Deterministic runs for reproducibility.
    random.seed(0)

    workloads = make_workloads()
    runs: List[Dict[str, Any]] = []

    for wl_id, wl in workloads.items():
        # Baseline
        baseline_agent = wl.agent_factory_baseline()
        baseline_run_id = make_run_id(f"{wl_id}-baseline")
        baseline_result = run_unbounded(wl.input_prompt, baseline_agent)

        runs.append(
            {
                "variant": "baseline",
                "workload_id": wl_id,
                "run_id": baseline_run_id,
                "success": bool(baseline_result.stop_reason == "agent_converged"),
                "metrics": {
                    "steps_taken": float(baseline_result.steps_taken),
                    "tool_calls_made": float(baseline_result.tool_calls_made),
                    "wall_time": float(baseline_result.wall_time),
                    "llm_tokens_used": float(baseline_result.llm_tokens_used),
                },
                "stop_reason": baseline_result.stop_reason,
            }
        )

        # Treatment
        treatment_agent = wl.agent_factory_treatment()
        orchestrator = BudgetedOrchestrator(budget=wl.treatment_budget, agent=treatment_agent)
        treatment_run_id = make_run_id(f"{wl_id}-treatment")
        treatment_result = orchestrator.run(wl.input_prompt)

        runs.append(
            {
                "variant": "treatment",
                "workload_id": wl_id,
                "run_id": treatment_run_id,
                "success": bool(treatment_result.stop_reason == "agent_converged"),
                "metrics": {
                    "steps_taken": float(treatment_result.steps_taken),
                    "tool_calls_made": float(treatment_result.tool_calls_made),
                    "wall_time": float(treatment_result.wall_time),
                    "llm_tokens_used": float(treatment_result.llm_tokens_used),
                    "rate_limit_violations_detected": float(
                        treatment_result.rate_limit_violations_detected
                    ),
                    "budget_violations_detected": float(
                        treatment_result.budget_violations_detected
                    ),
                },
                "stop_reason": treatment_result.stop_reason,
            }
        )

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.system(),
            "python": sys.version.split()[0],
        },
        "runs": runs,
        "notes": (
            "All runs executed in an offline sandbox using deterministic agent stubs "
            "and a budgeted orchestrator. Metrics are directly measured from these "
            "executions; no external APIs were contacted."
        ),
    }

    return evidence


def main() -> None:  # pragma: no cover - integration function
    evidence = run_experiment_suite()

    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    out_path = os.path.join(evidence_dir, "results.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":  # pragma: no cover
    main()
