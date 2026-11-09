from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .agent import MonitoredAgent, SimpleAgent, Task, ToolRunner
from .monitoring import (
    CircuitBreaker,
    CircuitBreakerConfig,
    EmergencyShutdownManager,
    MetricsRecorder,
    Monitor,
)
from .workloads import WORKLOADS, get_workload


AVAILABLE_WORKLOADS = list(WORKLOADS.keys())


def _build_baseline_components() -> Dict[str, Any]:
    recorder = MetricsRecorder(window_error_rate=20, window_latency=10)
    monitor = Monitor(recorder)
    runner = ToolRunner()
    agent = SimpleAgent(tool_runner=runner, monitor=monitor)
    return {"agent": agent, "monitor": monitor}


def _build_treatment_components() -> Dict[str, Any]:
    recorder = MetricsRecorder(window_error_rate=20, window_latency=10)
    monitor = Monitor(recorder)
    breaker_cfg = CircuitBreakerConfig(
        error_rate_threshold_window_20=0.5,
        latency_threshold_window_10_ms=250.0,
        min_samples_for_decision=10,
    )
    breaker = CircuitBreaker(config=breaker_cfg)
    shutdown = EmergencyShutdownManager(policy_violation_shutdown_enabled=True)
    runner = ToolRunner()
    agent = MonitoredAgent(
        tool_runner=runner,
        monitor=monitor,
        breaker=breaker,
        shutdown_manager=shutdown,
    )
    return {
        "agent": agent,
        "monitor": monitor,
        "breaker": breaker,
        "shutdown": shutdown,
        "config": breaker_cfg,
    }


def run_single_experiment(workload_id: str, mode: str) -> Dict[str, Any]:
    if workload_id not in WORKLOADS:
        raise ValueError(f"Unknown workload: {workload_id}")
    workload = get_workload(workload_id)
    tasks: List[Task] = workload.generate_tasks()

    start_wall = time.time()

    if mode == "baseline":
        comps = _build_baseline_components()
        agent: SimpleAgent = comps["agent"]
        monitor: Monitor = comps["monitor"]
        events = agent.run(tasks)
        breaker_open_transitions = 0
        time_to_first_open: Any = None
        shutdown_triggered = False
        shutdown_state = "N/A"
        cfg = {
            "error_rate_threshold_window_20": 0.5,
            "latency_threshold_window_10_ms": 250.0,
            "window_sizes": {"error_rate_window": 20, "latency_window": 10},
            "policy_violation_shutdown_enabled": False,
            "max_tasks": len(tasks),
        }
    elif mode == "treatment":
        comps = _build_treatment_components()
        agent: MonitoredAgent = comps["agent"]
        monitor: Monitor = comps["monitor"]
        breaker: CircuitBreaker = comps["breaker"]
        shutdown: EmergencyShutdownManager = comps["shutdown"]
        events = agent.run(tasks)
        breaker_open_transitions = breaker.open_transitions
        time_to_first_open = breaker.first_open_task_index
        shutdown_triggered = shutdown.is_terminated
        shutdown_state = shutdown.state
        cfg_obj: CircuitBreakerConfig = comps["config"]
        cfg = {
            "error_rate_threshold_window_20": cfg_obj.error_rate_threshold_window_20,
            "latency_threshold_window_10_ms": cfg_obj.latency_threshold_window_10_ms,
            "window_sizes": {
                "error_rate_window": monitor.metrics.window_error_rate,
                "latency_window": monitor.metrics.window_latency,
            },
            "policy_violation_shutdown_enabled": shutdown.policy_violation_shutdown_enabled,
            "max_tasks": len(tasks),
        }
    else:
        raise ValueError(f"Unknown mode: {mode}")

    end_wall = time.time()

    metrics = monitor.metrics

    tasks_scheduled = len(tasks)
    tasks_executed = len(events)
    error_rate_overall = metrics.overall_error_rate
    error_rate_window_20 = metrics.error_rate_window
    rolling_mean_latency_window_10 = metrics.rolling_mean_latency
    policy_violation_events = metrics.policy_violations

    post_trigger_tasks_executed = 0
    if mode == "treatment":
        idx_trigger = None
        if time_to_first_open is not None:
            idx_trigger = time_to_first_open
        if shutdown_triggered and idx_trigger is None and events:
            idx_trigger = events[-1].task_index
        if idx_trigger is not None:
            post_trigger_tasks_executed = max(0, tasks_executed - idx_trigger)

    aggregate = {
        "tasks_scheduled": tasks_scheduled,
        "tasks_executed": tasks_executed,
        "error_rate_overall": error_rate_overall,
        "error_rate_window_20": error_rate_window_20,
        "rolling_mean_latency_window_10": rolling_mean_latency_window_10,
        "policy_violation_events": policy_violation_events,
        "breaker_open_transitions": breaker_open_transitions,
        "time_to_first_open": time_to_first_open,
        "shutdown_triggered": shutdown_triggered,
        "post_trigger_tasks_executed": post_trigger_tasks_executed,
        "total_wall_clock_runtime_ms": (end_wall - start_wall) * 1000.0,
        "final_shutdown_state": shutdown_state,
    }

    per_task_events = [e.to_dict() for e in events]

    result: Dict[str, Any] = {
        "workload_name": workload_id,
        "mode": mode,
        "config": cfg,
        "aggregate_metrics": aggregate,
        "per_task_events": per_task_events,
        "notes": "Experimental run for circuit breaker comparison.",
    }
    return result


def _write_result_file(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    workload_name = result["workload_name"]
    mode = result["mode"]
    path = output_dir / f"{workload_name}_{mode}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run chapter 12 experiments.")
    parser.add_argument(
        "--mode",
        choices=["baseline", "treatment", "both"],
        default="both",
        help="Which agent variant to run.",
    )
    parser.add_argument(
        "--workload",
        choices=AVAILABLE_WORKLOADS + ["ALL"],
        default="ALL",
        help="Which workload to run.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to store detailed result JSON files.",
    )

    args = parser.parse_args(argv)
    workloads = AVAILABLE_WORKLOADS if args.workload == "ALL" else [args.workload]
    modes: List[str]
    if args.mode == "both":
        modes = ["baseline", "treatment"]
    else:
        modes = [args.mode]

    out_dir = Path(args.output_dir)

    for workload_id in workloads:
        for mode in modes:
            print(f"Running {workload_id} [{mode}]...")
            result = run_single_experiment(workload_id, mode)
            _write_result_file(result, out_dir)
            agg = result["aggregate_metrics"]
            print(
                f"  tasks_executed={agg['tasks_executed']}, "
                f"errors_overall={agg['error_rate_overall']:.2f}, "
                f"breaker_open_transitions={agg['breaker_open_transitions']}, "
                f"shutdown_triggered={agg['shutdown_triggered']}"
            )


if __name__ == "__main__":  # pragma: no cover
    main()
