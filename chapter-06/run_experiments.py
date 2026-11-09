from __future__ import annotations

"""CLI runner for the bounded vs unbounded agent experiments.

This script is *not* used by the grading harness but is provided for humans
and for alignment with the chapter description. It prints a simple summary
and writes JSONL records under `results/`.
"""

import argparse
import json
import os
import platform
import time
from typing import Any, Dict, List

from baseline_unbounded_agent import run_unbounded
from bounded_orchestrator import BudgetedOrchestrator
from workloads import make_workloads
from results_utils import make_run_id


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run_all(workload_filter: str | None = None, verbose: bool = False) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    workloads = make_workloads()

    for wl_name, wl in workloads.items():
        if workload_filter and workload_filter != wl_name:
            continue

        print(f"=== Running workload {wl_name} ===")
        records: List[Dict[str, Any]] = []

        for rep in range(wl.repetitions):
            # Baseline
            baseline_agent = wl.agent_factory_baseline()
            baseline_run_id = make_run_id(f"{wl_name}-baseline-r{rep}")
            baseline_result = run_unbounded(wl.input_prompt, baseline_agent)

            if verbose:
                print(
                    f"Baseline {baseline_run_id}: steps={baseline_result.steps_taken}, "
                    f"tools={baseline_result.tool_calls_made}, stop={baseline_result.stop_reason}"
                )

            records.append(
                {
                    "run_id": baseline_run_id,
                    "workload_name": wl.name,
                    "agent_mode": "baseline_unbounded",
                    "config": {
                        "budget_config": None,
                        "tool_config": {},
                        "agent_variant": type(baseline_agent).__name__,
                        "seed": 0,
                    },
                    "metrics": {
                        "steps_taken": baseline_result.steps_taken,
                        "llm_tokens_used": baseline_result.llm_tokens_used,
                        "tool_calls_made": baseline_result.tool_calls_made,
                        "wall_time": baseline_result.wall_time,
                        "stop_reason": baseline_result.stop_reason,
                        "rate_limit_violations_detected": 0,
                        "budget_violations_detected": 0,
                        "successful_task_completion": baseline_result.stop_reason
                        == "agent_converged",
                    },
                }
            )

            # Treatment
            treatment_agent = wl.agent_factory_treatment()
            orchestrator = BudgetedOrchestrator(budget=wl.treatment_budget, agent=treatment_agent)
            treatment_run_id = make_run_id(f"{wl_name}-treatment-r{rep}")
            treatment_result = orchestrator.run(wl.input_prompt)

            if verbose:
                print(
                    f"Treatment {treatment_run_id}: steps={treatment_result.steps_taken}, "
                    f"tools={treatment_result.tool_calls_made}, stop={treatment_result.stop_reason}"
                )

            records.append(
                {
                    "run_id": treatment_run_id,
                    "workload_name": wl.name,
                    "agent_mode": "treatment_bounded",
                    "config": {
                        "budget_config": {
                            "max_steps": wl.treatment_budget.max_steps,
                            "max_llm_tokens": wl.treatment_budget.max_llm_tokens,
                            "max_tool_calls": wl.treatment_budget.max_tool_calls,
                            "max_calls_per_minute": wl.treatment_budget.max_calls_per_minute,
                            "max_wall_time_s": wl.treatment_budget.max_wall_time_s,
                        },
                        "tool_config": {},
                        "agent_variant": type(treatment_agent).__name__,
                        "seed": 0,
                    },
                    "metrics": {
                        "steps_taken": treatment_result.steps_taken,
                        "llm_tokens_used": treatment_result.llm_tokens_used,
                        "tool_calls_made": treatment_result.tool_calls_made,
                        "wall_time": treatment_result.wall_time,
                        "stop_reason": treatment_result.stop_reason,
                        "rate_limit_violations_detected": treatment_result.rate_limit_violations_detected,
                        "budget_violations_detected": treatment_result.budget_violations_detected,
                        "successful_task_completion": treatment_result.stop_reason
                        == "agent_converged",
                    },
                }
            )

        out_path = os.path.join(RESULTS_DIR, f"{wl_name}.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        print(f"Wrote {len(records)} records to {out_path}")


def main() -> None:  # pragma: no cover - thin CLI
    parser = argparse.ArgumentParser(description="Run chapter 06 experiments")
    parser.add_argument("--workload", type=str, default=None, help="Specific workload ID to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    start = time.time()
    run_all(workload_filter=args.workload, verbose=args.verbose)
    elapsed = time.time() - start
    print(f"All experiments completed in {elapsed:.2f}s on {platform.system()} {platform.release()}")


if __name__ == "__main__":  # pragma: no cover
    main()
