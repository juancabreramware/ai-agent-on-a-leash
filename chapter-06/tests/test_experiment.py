from __future__ import annotations

"""End-to-end tests for the chapter 06 experiment.

These tests validate that:
- `run.py` produces evidence at the expected path with the expected schema.
- At least one baseline and one treatment run exist per workload.
- All metrics values are numeric (int or float).

`unittest` is used as required by the harness.
"""

import json
import os
import tempfile
import unittest
from typing import Dict

import run as run_module
from workloads import make_workloads


class TestExperimentEvidenceSchema(unittest.TestCase):
    def test_run_py_produces_valid_evidence(self) -> None:
        # Use a temporary directory as BOOKMAS_EVIDENCE_DIR
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["BOOKMAS_EVIDENCE_DIR"] = tmpdir

            _ = run_module.run_experiment_suite()

            # Write via run.main() semantics to ensure same code path works.
            run_module.main()

            out_path = os.path.join(tmpdir, "results.json")
            self.assertTrue(os.path.exists(out_path), "results.json must be created")

            with open(out_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

        # Basic top-level keys
        self.assertEqual(loaded["chapter"], 6)
        self.assertEqual(
            loaded["experiment_id"],
            "exp-06-bounded-loops-budgets-rate-limits-v1",
        )
        self.assertIn("environment", loaded)
        self.assertIn("runs", loaded)
        self.assertIsInstance(loaded["runs"], list)

        workloads = make_workloads()
        # Track which workloads have baseline/treatment
        seen: Dict[str, Dict[str, bool]] = {
            wid: {"baseline": False, "treatment": False} for wid in workloads.keys()
        }

        for rec in loaded["runs"]:
            workload_id = rec["workload_id"]
            self.assertIn(workload_id, workloads)

            variant = rec["variant"]
            self.assertIn(variant, ("baseline", "treatment"))
            seen[workload_id][variant] = True

            # Schema checks
            self.assertIn("run_id", rec)
            self.assertIn("success", rec)
            self.assertIn("metrics", rec)

            metrics = rec["metrics"]
            self.assertIsInstance(metrics, dict)

            for k, v in metrics.items():
                # Metrics must be numeric only
                self.assertIsInstance(
                    v,
                    (int, float),
                    msg=f"Metric {k} must be numeric, got {type(v)}",
                )

        # Ensure every workload has both baseline and treatment runs
        for wid, flags in seen.items():
            self.assertTrue(flags["baseline"], f"Workload {wid} missing baseline run")
            self.assertTrue(flags["treatment"], f"Workload {wid} missing treatment run")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
