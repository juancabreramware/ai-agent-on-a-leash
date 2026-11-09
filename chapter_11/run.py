import json
import os
import platform
from pathlib import Path

from chapter_11.experiment import run_full_experiment


def main() -> None:
    # Run the internal experiment harness to obtain per-workload metrics.
    results = run_full_experiment()

    # Prepare evidence directory and path. The validator specifies that
    # evidence is written to /evidence/results.json, but also mentions an
    # environment variable BOOKMAS_EVIDENCE_DIR. We respect the environment
    # variable if set, defaulting to "/evidence".
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    evidence_path = Path(evidence_dir) / "results.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    evidence = {
        "chapter": 11,
        "experiment_id": "exp-11-independent-verification-multi-agent-supervision",
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
        },
        "runs": [],
        "notes": (
            "Deterministic offline experiment comparing baseline vs. "
            "supervised agents under three workloads. Metrics are counts "
            "of unsafe and total approved actions per workload."
        ),
    }

    for run in results:
        # Each run dict already has the required fields and numeric metrics.
        evidence["runs"].append(run)

    with evidence_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
