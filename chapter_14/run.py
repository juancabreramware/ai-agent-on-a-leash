import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from chapter14.baseline_orchestrator import BaselineOrchestrator
from chapter14.recovery_orchestrator import RecoveryOrchestrator
from chapter14.workloads import get_workload_profiles, make_initial_state_fixture
from chapter14.invariants import InvariantsEngine


CHAPTER_NUMBER = 14
EXPERIMENT_ID = "chap14-unsafe-recovery-01"


@dataclass
class RunResult:
    variant: str
    workload_id: str
    run_id: str
    success: bool
    metrics: Dict[str, float]


def run_single(variant: str, workload_id: str, seed: int) -> RunResult:
    # Prepare initial state and orchestrator
    initial_state = make_initial_state_fixture()
    engine = InvariantsEngine()

    if variant == "baseline":
        orchestrator = BaselineOrchestrator(seed=seed)
    elif variant == "treatment":
        orchestrator = RecoveryOrchestrator(seed=seed)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    profile = get_workload_profiles()[workload_id]

    start = time.perf_counter()
    final_state, info = orchestrator.run_workload(initial_state, profile)
    duration = time.perf_counter() - start

    # Evaluate invariants offline on final state
    violations = engine.count_violations(final_state)

    # success flag: treatment succeeds if it did not end with violations
    # baseline succeeds if it simply completed (even if violations exist)
    if variant == "treatment":
        success = violations == 0
    else:
        success = True

    run_id = f"{workload_id}_{variant}_seed{seed}"

    metrics: Dict[str, float] = {
        "duration_seconds": float(duration),
        "final_invariant_violations": float(violations),
    }

    return RunResult(
        variant=variant,
        workload_id=workload_id,
        run_id=run_id,
        success=bool(success),
        metrics=metrics,
    )


def main() -> None:
    # Simple deterministic seeds per workload
    workload_profiles = get_workload_profiles()
    seeds = {
        "WL1_nominal_no_corruption": 42,
        "WL2_immediate_corruption_after_safe_start": 43,
        "WL3_late_corruption_after_long_run": 44,
        "WL4_hidden_side_effect_external_view": 45,
    }

    runs: List[Dict[str, Any]] = []

    for workload_id in sorted(workload_profiles.keys()):
        seed = seeds[workload_id]
        for variant in ("baseline", "treatment"):
            result = run_single(variant, workload_id, seed)
            runs.append(
                {
                    "variant": result.variant,
                    "workload_id": result.workload_id,
                    "run_id": result.run_id,
                    "success": result.success,
                    "metrics": result.metrics,
                }
            )

    env_info = {
        "os": os.name,
        "python": sys.version.split()[0],
    }

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": env_info,
        "runs": runs,
        "notes": (
            "Metrics include per-run duration_seconds and final_invariant_violations. "
            "All values are measured from actual execution in this environment."
        ),
    }

    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    out_path = os.path.join(evidence_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)


if __name__ == "__main__":
    main()
