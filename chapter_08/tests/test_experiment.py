import json
import os
import unittest
from pathlib import Path


class ExperimentEvidenceSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        # Use a temporary evidence directory under /tmp to avoid clashes
        self.evidence_dir = Path("/tmp") / "chapter08_evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        os.environ["BOOKMAS_EVIDENCE_DIR"] = str(self.evidence_dir)

    def _run_script(self) -> None:
        import run  # noqa: F401 - imported for side effect of executing main when called directly
        # Explicitly call main to avoid confusing import semantics
        run.main()

    def test_results_json_schema(self) -> None:
        self._run_script()
        results_path = self.evidence_dir / "results.json"
        self.assertTrue(results_path.exists(), "run.py must create results.json in evidence directory")

        with results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys
        self.assertEqual(data.get("chapter"), 8)
        self.assertEqual(data.get("experiment_id"), "exp-08-transactional-execution-reversible-actions-v1")
        self.assertIn("environment", data)
        self.assertIsInstance(data["environment"], dict)
        self.assertIn("os", data["environment"])
        self.assertIn("python", data["environment"])

        self.assertIn("runs", data)
        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)

        # Ensure at least one baseline and one treatment per workload
        variants_by_workload = {}
        for run in runs:
            self.assertIn("variant", run)
            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIsInstance(run.get("success"), bool)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIsInstance(run["run_id"], str)

            metrics = run.get("metrics")
            self.assertIsInstance(metrics, dict)
            for k, v in metrics.items():
                # All metric values must be numbers
                self.assertIsInstance(v, (int, float), f"Metric {k} must be numeric")

            wl = run["workload_id"]
            variants_by_workload.setdefault(wl, set()).add(run["variant"])

        for wl, variants in variants_by_workload.items():
            self.assertIn("baseline", variants, f"Workload {wl} missing baseline run")
            self.assertIn("treatment", variants, f"Workload {wl} missing treatment run")


if __name__ == "__main__":
    unittest.main()
