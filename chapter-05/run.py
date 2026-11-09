from __future__ import annotations

import json
import os
import platform
import sys
from typing import Any, Dict, List

from sandbox_runner import run_all_workloads, executed_run_to_record


EXPERIMENT_ID = "exp-ch05-sandboxed-execution-v1"
CHAPTER = 5


def main() -> None:
    # Execute workloads under baseline and treatment
    executed = run_all_workloads()

    runs: List[Dict[str, Any]] = []
    for erun in executed:
        rec = executed_run_to_record(erun)
        runs.append(rec)

    # Build evidence structure
    evidence: Dict[str, Any] = {
        "chapter": CHAPTER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
        },
        "runs": runs,
        "notes": "Execution performed via run.py in offline sandbox; metrics are per-run wall-clock durations only.",
    }

    # Determine evidence directory
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    output_path = os.path.join(evidence_dir, "results.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    print(f"Wrote evidence to {output_path}")


if __name__ == "__main__":
    main()
