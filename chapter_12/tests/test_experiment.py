import json
import os
import unittest
from pathlib import Path

from chapter_12_circuit_breakers.monitoring import (
    CircuitBreaker,
    CircuitBreakerConfig,
    EmergencyShutdownManager,
    MetricsRecorder,
    Monitor,
    TaskEvent,
    BreakerState,
)
from chapter_12_circuit_breakers.agent import SimpleAgent, MonitoredAgent, ToolRunner, Task
from chapter_12_circuit_breakers.workloads import (
    get_workload,
    WORKLOADS,
)
from run import main as run_main


class TestMetricsAndBreaker(unittest.TestCase):
    def test_metrics_recorder_windows(self) -> None:
        recorder = MetricsRecorder(window_error_rate=3, window_latency=2)
        monitor = Monitor(recorder)

        # Create synthetic events with known success/failure and latency.
        base = {
            "task_id": "t",
            "task_type": "success",
            "start_time": 0.0,
            "end_time": 1.0,
            "breaker_state_before": "N/A",
            "breaker_state_after": "N/A",
            "shutdown_state": "N/A",
            "error_type": None,
            "policy_violation": False,
        }

        events = [
            TaskEvent(task_index=1, latency_ms=100.0, success=True, **base),
            TaskEvent(task_index=2, latency_ms=200.0, success=False, **base),
            TaskEvent(task_index=3, latency_ms=300.0, success=False, **base),
        ]
        for e in events:
            monitor.record_event(e)

        self.assertEqual(recorder.total_tasks, 3)
        self.assertEqual(recorder.total_failures, 2)
        # Window error rate: last 3 events, 2 failures.
        self.assertAlmostEqual(recorder.error_rate_window, 2 / 3)
        # Latency window size 2, last 2 events 200, 300.
        self.assertAlmostEqual(recorder.rolling_mean_latency, (200.0 + 300.0) / 2.0)

    def test_circuit_breaker_opens_on_error_rate(self) -> None:
        recorder = MetricsRecorder(window_error_rate=4, window_latency=10)
        monitor = Monitor(recorder)
        cfg = CircuitBreakerConfig(
            error_rate_threshold_window_20=0.5,
            latency_threshold_window_10_ms=1000.0,
            min_samples_for_decision=2,
        )
        breaker = CircuitBreaker(cfg)

        base = {
            "task_id": "t",
            "task_type": "success",
            "start_time": 0.0,
            "end_time": 1.0,
            "breaker_state_before": "N/A",
            "breaker_state_after": "N/A",
            "shutdown_state": "N/A",
            "error_type": None,
            "policy_violation": False,
        }

        # First success
        monitor.record_event(TaskEvent(task_index=1, latency_ms=10.0, success=True, **base))
        breaker.evaluate(monitor)
        self.assertEqual(breaker.state, BreakerState.CLOSED)

        # Next three failures -> error rate 75%
        for i in range(2, 5):
            monitor.record_event(TaskEvent(task_index=i, latency_ms=10.0, success=False, **base))
            breaker.evaluate(monitor)

        self.assertEqual(breaker.state, BreakerState.OPEN)
        self.assertEqual(breaker.open_transitions, 1)
        self.assertIsNotNone(breaker.first_open_task_index)


class TestAgentsAndWorkloads(unittest.TestCase):
    def test_wl1_baseline_vs_treatment_tasks_executed_equal(self) -> None:
        wl1 = get_workload("WL1_nominal_low_error")
        tasks = wl1.generate_tasks()

        # Baseline
        recorder_b = MetricsRecorder(window_error_rate=20, window_latency=10)
        monitor_b = Monitor(recorder_b)
        agent_b = SimpleAgent(ToolRunner(), monitor_b)
        events_b = agent_b.run(tasks)

        # Treatment with thresholds chosen to avoid trips for WL1
        recorder_t = MetricsRecorder(window_error_rate=20, window_latency=10)
        monitor_t = Monitor(recorder_t)
        cfg = CircuitBreakerConfig(
            error_rate_threshold_window_20=0.9,
            latency_threshold_window_10_ms=1000.0,
            min_samples_for_decision=10,
        )
        breaker = CircuitBreaker(cfg)
        shutdown = EmergencyShutdownManager(policy_violation_shutdown_enabled=True)
        agent_t = MonitoredAgent(ToolRunner(), monitor_t, breaker, shutdown)
        # Use fresh tasks (generator is deterministic, but we re-generate for clarity)
        tasks_t = wl1.generate_tasks()
        events_t = agent_t.run(tasks_t)

        self.assertEqual(len(events_b), len(events_t))
        self.assertEqual(len(events_b), len(tasks))
        self.assertEqual(breaker.open_transitions, 0)
        self.assertFalse(shutdown.is_terminated)

    def test_wl4_policy_violation_triggers_shutdown(self) -> None:
        wl4 = get_workload("WL4_immediate_policy_violation")
        tasks = wl4.generate_tasks()

        recorder = MetricsRecorder(window_error_rate=20, window_latency=10)
        monitor = Monitor(recorder)
        cfg = CircuitBreakerConfig(
            error_rate_threshold_window_20=0.5,
            latency_threshold_window_10_ms=250.0,
            min_samples_for_decision=1,
        )
        breaker = CircuitBreaker(cfg)
        shutdown = EmergencyShutdownManager(policy_violation_shutdown_enabled=True)
        agent = MonitoredAgent(ToolRunner(), monitor, breaker, shutdown)

        events = agent.run(tasks)
        # Should stop shortly after policy violation at index 3.
        self.assertLessEqual(len(events), len(tasks))
        self.assertTrue(any(e["policy_violation"] for e in [ev.to_dict() for ev in events]))
        self.assertTrue(shutdown.is_terminated)
        # No tasks should execute after termination.
        last_index = events[-1].task_index
        self.assertLessEqual(last_index, 4)


class TestEvidenceSchema(unittest.TestCase):
    def test_run_py_produces_valid_evidence(self) -> None:
        # Use a temporary evidence directory under the test workspace.
        tmp_dir = Path(".test_evidence")
        tmp_dir.mkdir(exist_ok=True)
        os.environ["BOOKMAS_EVIDENCE_DIR"] = str(tmp_dir)

        # Run the main evidence generator.
        run_main()

        evidence_path = tmp_dir / "results.json"
        self.assertTrue(evidence_path.exists(), "results.json not created")

        with evidence_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Basic top-level keys
        self.assertEqual(data["chapter"], 12)
        self.assertEqual(
            data["experiment_id"],
            "exp-12-continuous-monitoring-circuit-breaker-shutdown",
        )
        self.assertIn("environment", data)
        self.assertIn("runs", data)
        self.assertIsInstance(data["runs"], list)

        runs = data["runs"]
        self.assertGreaterEqual(len(runs), 2)

        # Ensure at least one baseline and one treatment run per workload.
        seen = {}
        for r in runs:
            workload_id = r["workload_id"]
            variant = r["variant"]
            seen.setdefault(workload_id, set()).add(variant)

            # Schema for each run
            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIsInstance(r["run_id"], str)
            self.assertIn("success", r)
            self.assertIsInstance(r["success"], bool)

            metrics = r["metrics"]
            self.assertIsInstance(metrics, dict)
            # All metric values must be numbers.
            for v in metrics.values():
                self.assertIsInstance(v, (int, float))

        for workload_id in WORKLOADS.keys():
            self.assertIn(workload_id, seen)
            self.assertIn("baseline", seen[workload_id])
            self.assertIn("treatment", seen[workload_id])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
