from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from .agent import Task


RANDOM_SEED = 12345


@dataclass
class Workload:
    name: str

    def generate_tasks(self) -> List[Task]:  # pragma: no cover - overridden
        raise NotImplementedError


class WL1NominalLowError(Workload):
    def __init__(self) -> None:
        super().__init__(name="WL1_nominal_low_error")

    def generate_tasks(self) -> List[Task]:
        rnd = random.Random(RANDOM_SEED)
        total_tasks = 50
        tasks: List[Task] = []
        for i in range(total_tasks):
            # 90% success, 10% slow
            if rnd.random() < 0.9:
                task_type = "success"
                latency = rnd.randint(5, 20)
            else:
                task_type = "slow"
                latency = rnd.randint(80, 150)
            tasks.append(Task(task_id=f"WL1-{i+1}", task_type=task_type, latency_ms=latency))
        return tasks


class WL2ErrorSpike(Workload):
    def __init__(self) -> None:
        super().__init__(name="WL2_error_spike")

    def generate_tasks(self) -> List[Task]:
        rnd = random.Random(RANDOM_SEED)
        tasks: List[Task] = []

        # Warmup: 30 success
        for i in range(30):
            latency = rnd.randint(5, 20)
            tasks.append(Task(task_id=f"WL2-warmup-{i+1}", task_type="success", latency_ms=latency))

        # Error spike: 20 failing
        for i in range(20):
            latency = rnd.randint(5, 20)
            tasks.append(Task(task_id=f"WL2-spike-{i+1}", task_type="failing", latency_ms=latency))

        # Post spike: 50 success
        for i in range(50):
            latency = rnd.randint(5, 20)
            tasks.append(Task(task_id=f"WL2-post-{i+1}", task_type="success", latency_ms=latency))

        return tasks


class WL3LatencySurge(Workload):
    def __init__(self) -> None:
        super().__init__(name="WL3_latency_surge")

    def generate_tasks(self) -> List[Task]:
        rnd = random.Random(RANDOM_SEED)
        tasks: List[Task] = []

        # Baseline latency: 30 success
        for i in range(30):
            latency = rnd.randint(50, 80)
            tasks.append(Task(task_id=f"WL3-base-{i+1}", task_type="success", latency_ms=latency))

        # Latency surge: 30 slow
        for i in range(30):
            latency = rnd.randint(300, 500)
            tasks.append(Task(task_id=f"WL3-surge-{i+1}", task_type="slow", latency_ms=latency))

        # Post surge: 20 success
        for i in range(20):
            latency = rnd.randint(50, 80)
            tasks.append(Task(task_id=f"WL3-post-{i+1}", task_type="success", latency_ms=latency))

        return tasks


class WL4ImmediatePolicyViolation(Workload):
    def __init__(self) -> None:
        super().__init__(name="WL4_immediate_policy_violation")

    def generate_tasks(self) -> List[Task]:
        # Fixed sequence, deterministic latencies.
        seq = [
            "success",
            "success",
            "policy_violation",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
            "success",
        ]
        tasks: List[Task] = []
        base_latency = 20
        for i, ttype in enumerate(seq, start=1):
            latency = base_latency
            tasks.append(Task(task_id=f"WL4-{i}", task_type=ttype, latency_ms=latency))
        return tasks


WORKLOADS = {
    "WL1_nominal_low_error": WL1NominalLowError(),
    "WL2_error_spike": WL2ErrorSpike(),
    "WL3_latency_surge": WL3LatencySurge(),
    "WL4_immediate_policy_violation": WL4ImmediatePolicyViolation(),
}


def get_workload(name: str) -> Workload:
    if name not in WORKLOADS:
        raise ValueError(f"Unknown workload: {name}")
    return WORKLOADS[name]
