import json
import os
import sys
import types
import unittest


class TestExperimentEvidenceSchema(unittest.TestCase):
    def test_run_py_writes_valid_evidence(self) -> None:
        # Ensure evidence directory exists
        evidence_dir = "/evidence"
        os.makedirs(evidence_dir, exist_ok=True)
        out_path = os.path.join(evidence_dir, "results.json")
        if os.path.exists(out_path):
            os.remove(out_path)

        # Import and run main from run.py
        import run  # type: ignore

        self.assertTrue(hasattr(run, "main"))
        self.assertIsInstance(run.main, types.FunctionType)
        run.main()

        # Evidence file must exist
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level checks
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("chapter"), 14)
        self.assertEqual(data.get("experiment_id"), "chap14-unsafe-recovery-01")
        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 8)  # 4 workloads * 2 variants

        # Track that each workload has baseline and treatment
        seen = {}
        for run_rec in runs:
            self.assertIsInstance(run_rec, dict)
            variant = run_rec.get("variant")
            workload_id = run_rec.get("workload_id")
            run_id = run_rec.get("run_id")
            success = run_rec.get("success")
            metrics = run_rec.get("metrics")

            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIsInstance(workload_id, str)
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(metrics, dict)

            # All metrics must be finite JSON numbers (no strings/bools/dicts/lists)
            self.assertGreater(len(metrics), 0)
            for k, v in metrics.items():
                self.assertIsInstance(k, str)
                self.assertIsInstance(v, (int, float))

            key = (workload_id, variant)
            seen[key] = True

        # Ensure at least one baseline and one treatment per workload
        workloads = {
            "WL1_nominal_no_corruption",
            "WL2_immediate_corruption_after_safe_start",
            "WL3_late_corruption_after_long_run",
            "WL4_hidden_side_effect_external_view",
        }
        for wid in workloads:
            self.assertTrue(seen.get((wid, "baseline")))
            self.assertTrue(seen.get((wid, "treatment")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
