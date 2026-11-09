import json
import os
import platform
from typing import Any, Dict, List

from runner import run_full_experiment


def main() -> None:
    # Run a small but complete experiment: 1 repetition per workload/variant
    runs: List[Dict[str, Any]] = run_full_experiment(repetitions=1)

    evidence: Dict[str, Any] = {
        "chapter": 7,
        "experiment_id": "ch07-deterministic-state-machines-vs-free-form-agents",
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "runs": runs,
    }

    notes = "All metrics are computed from deterministic mock agents and tools in an offline sandbox."
    evidence["notes"] = notes

    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    out_path = os.path.join(evidence_dir, "results.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)


if __name__ == "__main__":
    main()
