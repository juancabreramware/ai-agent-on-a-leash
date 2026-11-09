import json
import os
import tempfile
import unittest

from src.tools import reset_side_effect_store, get_side_effect_store
from src.workloads import (
    WORKLOAD_IDS,
    run_workload_baseline,
    run_workload_treatment,
)
import run as experiment_run


class TestWorkloadsAndEvidence(unittest.TestCase):
    def setUp(self) -> None:
        reset_side_effect_store()

    def test_baseline_and_treatment_runs_produce_numeric_metrics(self) -> None:
        for wid in WORKLOAD_IDS:
            reset_side_effect_store()
            b = run_workload_baseline(wid)
            t = run_workload_treatment(wid)
            self.assertTrue(b["success"])
            self.assertIsInstance(b["metrics"], dict)
            self.assertTrue(b["metrics"].keys())
            for v in b["metrics"].values():
                self.assertIsInstance(v, (int, float))

            self.assertIsInstance(t["metrics"], dict)
            self.assertTrue(t["metrics"].keys())
            for v in t["metrics"].values():
                self.assertIsInstance(v, (int, float))

    def test_treatment_prevents_unauthorized_execution(self) -> None:
        # For high-risk workloads, unauthorized_executed must be 0.
        for wid in [
            "WL1_auto_approve_high_risk",
            "WL2_auto_deny_high_risk",
            "WL3_timeout_no_response",
        ]:
            reset_side_effect_store()
            result = run_workload_treatment(wid)
            self.assertEqual(result["metrics"].get("unauthorized_executed"), 0.0)

    def test_run_py_writes_valid_evidence_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["BOOKMAS_EVIDENCE_DIR"] = tmpdir
            experiment_run.main()
            path = os.path.join(tmpdir, "results.json")
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Top-level keys
        self.assertEqual(data["chapter"], 9)
        self.assertEqual(data["experiment_id"], "exp-ch09-human-approval-gates-v1")
        self.assertIn("environment", data)
        self.assertIn("runs", data)
        self.assertIsInstance(data["runs"], list)

        # At least one baseline and one treatment per workload
        by_workload = {}
        for run in data["runs"]:
            wid = run["workload_id"]
            by_workload.setdefault(wid, set()).add(run["variant"])
            # Schema checks per run
            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIn("run_id", run)
            self.assertIsInstance(run["success"], bool)
            self.assertIsInstance(run["metrics"], dict)
            for k, v in run["metrics"].items():
                # Metrics must be numbers only
                self.assertIsInstance(v, (int, float), msg=f"Metric {k} not numeric")

        for wid in WORKLOAD_IDS:
            self.assertIn(wid, by_workload)
            self.assertIn("baseline", by_workload[wid])
            self.assertIn("treatment", by_workload[wid])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
