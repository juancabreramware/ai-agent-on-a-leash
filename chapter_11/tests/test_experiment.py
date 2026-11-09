import json
import os
import unittest
from pathlib import Path


class TestExperimentEvidence(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        # Ensure a clean evidence directory under /evidence.
        self.evidence_dir = Path(os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence"))
        self.evidence_file = self.evidence_dir / "results.json"
        if self.evidence_file.exists():
            self.evidence_file.unlink()

        # Run the experiment via run.py
        import run as experiment_run

        experiment_run.main()

    def test_evidence_file_exists(self) -> None:
        self.assertTrue(self.evidence_file.exists(), "results.json must be created by run.py")

    def test_evidence_schema(self) -> None:
        with self.evidence_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("chapter"), 11)
        self.assertEqual(
            data.get("experiment_id"),
            "exp-11-independent-verification-multi-agent-supervision",
        )

        # Environment
        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        # Runs
        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 6, "At least 2 variants x 3 workloads = 6 runs expected")

        # Per-run checks
        workloads_seen = {}
        for run in runs:
            self.assertIsInstance(run, dict)
            variant = run.get("variant")
            workload_id = run.get("workload_id")
            run_id = run.get("run_id")
            success = run.get("success")
            metrics = run.get("metrics")

            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIsInstance(workload_id, str)
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(metrics, dict)

            # Every metric must be numeric (int/float) and finite
            self.assertGreater(len(metrics), 0)
            for k, v in metrics.items():
                self.assertIsInstance(v, (int, float), f"Metric {k} must be numeric, got {type(v)}")

            # Collect variants per workload
            workloads_seen.setdefault(workload_id, set()).add(variant)

        # Ensure each known workload has both baseline and treatment
        expected_workloads = {
            "wl-11-1-low-risk-routine",
            "wl-11-2-mixed-benign-and-risky",
            "wl-11-3-adversarial-unsafe",
        }
        self.assertTrue(expected_workloads.issubset(set(workloads_seen.keys())))
        for wid in expected_workloads:
            variants = workloads_seen.get(wid, set())
            self.assertIn("baseline", variants, f"Workload {wid} missing baseline run")
            self.assertIn("treatment", variants, f"Workload {wid} missing treatment run")

    def test_treatment_not_worse_on_adversarial_unsafe_actions(self) -> None:
        """Sanity check: treatment should not approve more unsafe actions
        than baseline on the adversarial workload, under this deterministic
        stub implementation.
        """

        with self.evidence_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        runs = data["runs"]
        baseline_metrics = {}
        treatment_metrics = {}
        for run in runs:
            if run["workload_id"] == "wl-11-3-adversarial-unsafe":
                if run["variant"] == "baseline":
                    baseline_metrics = run["metrics"]
                elif run["variant"] == "treatment":
                    treatment_metrics = run["metrics"]

        self.assertTrue(baseline_metrics and treatment_metrics, "Both variants must exist for wl-11-3")

        b_unsafe_approved = baseline_metrics.get("unsafe_actions_approved")
        t_unsafe_approved = treatment_metrics.get("unsafe_actions_approved")
        self.assertIsInstance(b_unsafe_approved, (int, float))
        self.assertIsInstance(t_unsafe_approved, (int, float))

        self.assertLessEqual(
            t_unsafe_approved,
            b_unsafe_approved,
            "Treatment should not approve more unsafe actions than baseline on adversarial workload.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
