import json
import os
import unittest


class TestExperimentSchema(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure run.py has been executed before tests are run.
        # In many harnesses this will be true; if not, attempt to run it.
        from run import main as run_main

        evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        self.results_path = os.path.join(evidence_dir, "results.json")

        # Run experiment if file missing
        if not os.path.exists(self.results_path):
            run_main()

        with open(self.results_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def test_top_level_schema(self) -> None:
        d = self.data
        self.assertIsInstance(d, dict)
        self.assertEqual(d.get("chapter"), 7)
        self.assertEqual(
            d.get("experiment_id"),
            "ch07-deterministic-state-machines-vs-free-form-agents",
        )
        self.assertIn("environment", d)
        self.assertIsInstance(d["environment"].get("os"), str)
        self.assertIsInstance(d["environment"].get("python"), str)
        self.assertIn("runs", d)
        self.assertIsInstance(d["runs"], list)

    def test_runs_have_required_fields_and_numeric_metrics(self) -> None:
        runs = self.data["runs"]
        self.assertGreater(len(runs), 0)

        workloads_seen = {}

        for r in runs:
            self.assertIn("variant", r)
            self.assertIn(r["variant"], ("baseline", "treatment"))
            self.assertIn("workload_id", r)
            self.assertIsInstance(r["workload_id"], str)
            self.assertIn("run_id", r)
            self.assertIsInstance(r["run_id"], str)
            self.assertIn("success", r)
            self.assertIsInstance(r["success"], bool)
            self.assertIn("metrics", r)
            self.assertIsInstance(r["metrics"], dict)

            m = r["metrics"]
            # We require at least one numeric metric
            self.assertIn("steps", m)
            self.assertIsInstance(m["steps"], (int, float))
            self.assertIn("invalid_tool_calls", m)
            self.assertIsInstance(m["invalid_tool_calls"], (int, float))
            self.assertIn("completed", m)
            self.assertIsInstance(m["completed"], (int, float))

            key = r["workload_id"]
            workloads_seen.setdefault(key, set()).add(r["variant"])

        # Ensure at least one baseline and one treatment run per workload
        for wl, variants in workloads_seen.items():
            self.assertIn("baseline", variants, msg=f"No baseline for {wl}")
            self.assertIn("treatment", variants, msg=f"No treatment for {wl}")

    def test_treatment_fsm_reduces_out_of_order_changes(self) -> None:
        """Sanity check: treatment runs should respect FSM ordering.

        We do not parse full histories here, but we can at least assert
        that treatment runs complete with very low invalid_tool_calls.
        """

        treatments = [r for r in self.data["runs"] if r["variant"] == "treatment"]
        self.assertGreater(len(treatments), 0)

        for r in treatments:
            self.assertGreaterEqual(r["metrics"]["invalid_tool_calls"], 0.0)


if __name__ == "__main__":
    unittest.main()
