from typing import Dict, Any, List


def compute_run_metrics(run_log: Dict[str, Any]) -> Dict[str, float]:
    """Compute basic per-run numeric metrics.

    We restrict ourselves to simple metrics that can be computed
    deterministically without semantic understanding.
    """

    steps = int(run_log.get("steps", 0))
    invalid_tool_calls = int(run_log.get("invalid_tool_calls", 0))
    completed = bool(run_log.get("completed", False))

    return {
        "steps": float(steps),
        "invalid_tool_calls": float(invalid_tool_calls),
        "completed": 1.0 if completed else 0.0,
    }


def aggregate_metrics(runs: List[Dict[str, Any]]) -> Dict[str, float]:
    """Example aggregator, not used directly in run.py but available
    for chapter-level experimentation.

    Computes simple averages across runs.
    """

    if not runs:
        return {}

    totals: Dict[str, float] = {}
    count = float(len(runs))

    for r in runs:
        m = compute_run_metrics(r)
        for k, v in m.items():
            totals[k] = totals.get(k, 0.0) + float(v)

    return {k: v / count for k, v in totals.items()}
