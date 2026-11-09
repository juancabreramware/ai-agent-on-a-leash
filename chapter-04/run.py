import json
import os
import sys
import time
from typing import Any, Dict, List


def _detect_evidence_dir() -> str:
    env_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR")
    if env_dir:
        return env_dir
    # Fallback for the sandbox contract
    return "/evidence"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    # Import here so that this file stays small and clear
    from chap_04_policy_gateway.run_experiments import run_all_workloads

    evidence_dir = _detect_evidence_dir()
    _ensure_dir(evidence_dir)
    evidence_path = os.path.join(evidence_dir, "results.json")

    start = time.perf_counter()
    runs = run_all_workloads()
    total_elapsed_ms = (time.perf_counter() - start) * 1000.0

    environment = {
        "os": os.name,
        "python": sys.version.split()[0],
    }

    evidence: Dict[str, Any] = {
        "chapter": 4,
        "experiment_id": "exp-4-policy-gateway-v1",
        "environment": environment,
        "runs": runs,
        "notes": (
            "Experiment runs for chapter 4 policy gateway. "
            f"Total elapsed ms: {total_elapsed_ms:.3f}. "
            "Metrics are derived from actual execution; non-numeric "
            "metadata is kept outside the 'metrics' objects."
        ),
    }

    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
