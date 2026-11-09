from __future__ import annotations

"""Helpers for run IDs and basic aggregates."""

import random
import string
from statistics import mean, pstdev
from typing import Dict, Iterable, List


def make_run_id(prefix: str) -> str:
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"{prefix}-{suffix}"


def summarize_numeric(values: Iterable[float]) -> Dict[str, float]:
    lst: List[float] = list(values)
    if not lst:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0}
    if len(lst) == 1:
        v = float(lst[0])
        return {"min": v, "max": v, "mean": v, "stddev": 0.0}
    return {
        "min": float(min(lst)),
        "max": float(max(lst)),
        "mean": float(mean(lst)),
        "stddev": float(pstdev(lst)),
    }
