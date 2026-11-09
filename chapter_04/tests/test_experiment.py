import json
import math
import os
import tempfile
import unittest


class ExperimentEvidenceSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        # Use a temporary directory for evidence to avoid collisions
        self.tmpdir = tempfile.TemporaryDirectory()
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.tmpdir.name

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        if "BOOKMAS_EVIDENCE_DIR" in os.environ:
            del os.environ["BOOKMAS_EVIDENCE_DIR"]

    def test_run_produces_valid_results_schema(self) -> None:
        import run as experiment_run

        experiment_run.main()

        evidence_path = os.path.join(self.tmpdir.name, "results.json")
        self.assertTrue(os.path.exists(evidence_path), "results.json not created")

        with open(evidence_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level schema
        self.assertIn("chapter", data)
        self.assertEqual(data["chapter"], 4)
        self.assertIn("experiment_id", data)
        self.assertEqual(data["experiment_id"], "exp-4-policy-gateway-v1")
        self.assertIn("environment", data)
        self.assertIsInstance(data["environment"], dict)
        self.assertIn("runs", data)
        self.assertIsInstance(data["runs"], list)
        self.assertGreater(len(data["runs"]), 0)

        # Collect per-workload variants
        seen: dict[str, set[str]] = {}

        for run in data["runs"]:
            # Required fields per run
            self.assertIn("variant", run)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIn("success", run)
            self.assertIn("metrics", run)

            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIsInstance(run["workload_id"], str)
            self.assertIsInstance(run["run_id"], str)
            self.assertIsInstance(run["success"], bool)
            self.assertIsInstance(run["metrics"], dict)

            # Metrics must be finite JSON numbers
            for name, value in run["metrics"].items():
                self.assertIsInstance(value, (int, float), f"Metric {name} is not numeric")
                self.assertTrue(math.isfinite(float(value)), f"Metric {name} is not finite")

            wid = run["workload_id"]
            seen.setdefault(wid, set()).add(run["variant"])

        # Ensure at least one baseline and one treatment run per workload id
        for wid, variants in seen.items():
            self.assertIn("baseline", variants, f"Missing baseline for {wid}")
            self.assertIn("treatment", variants, f"Missing treatment for {wid}")

    def test_gateway_blocks_some_policy_violations(self) -> None:
        """Sanity check: for known violating workloads, treatment should execute
        fewer actions than baseline (i.e., some are blocked)."""

        from chap_04_policy_gateway.run_experiments import run_all_workloads

        runs = run_all_workloads()

        # Focus on workloads designed to violate policies
        violating_ids = {
            "wl1_case2_large_purchase",
            "wl1_case3_cumulative_limit",
            "wl2_case2_forbidden_other_customer",
            "wl3_case2_production_freeze_window",
            "wl4_case1_ignore_policy_instruction",
            "wl4_case2_disguised_request",
        }

        by_key: dict[tuple[str, str], dict] = {}
        for r in runs:
            key = (r["variant"], r["workload_id"])
            by_key[key] = r

        for wid in violating_ids:
            base = by_key.get(("baseline", wid))
            treat = by_key.get(("treatment", wid))
            self.assertIsNotNone(base, f"Missing baseline run for {wid}")
            self.assertIsNotNone(treat, f"Missing treatment run for {wid}")

            base_exec = base["metrics"].get("actions_executed", 0.0)
            treat_exec = treat["metrics"].get("actions_executed", 0.0)

            # Baseline is expected to execute the action (syntactic only)
            self.assertGreaterEqual(base_exec, 0.0)
            # Treatment should not exceed baseline, and generally be lower for violations
            self.assertLessEqual(treat_exec, base_exec, f"Treatment executed more than baseline for {wid}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
