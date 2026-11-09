import json
import os
import tempfile
import unittest

import run as experiment_run
from baseline_agent.llm_mock import WORKLOAD_IDS


class TestExperimentEvidenceSchema(unittest.TestCase):
    def test_run_generates_valid_evidence_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["BOOKMAS_EVIDENCE_DIR"] = tmpdir
            # Execute the experiment script
            experiment_run.main()

            path = os.path.join(tmpdir, "results.json")
            self.assertTrue(os.path.isfile(path), "results.json should be created")

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Top-level required keys
            self.assertEqual(data["chapter"], 10)
            self.assertEqual(data["experiment_id"], "exp-10-prompt-injection-guarded-agent-v1")
            self.assertIsInstance(data["environment"], dict)
            self.assertIn("os", data["environment"])
            self.assertIn("python", data["environment"])

            runs = data["runs"]
            self.assertIsInstance(runs, list)

            # At least one baseline and one treatment per workload
            for workload_id in WORKLOAD_IDS:
                matching = [r for r in runs if r["workload_id"] == workload_id]
                variants = {r["variant"] for r in matching}
                self.assertIn("baseline", variants)
                self.assertIn("treatment", variants)

            for run in runs:
                self.assertIn(run["variant"], ("baseline", "treatment"))
                self.assertIn(run["workload_id"], WORKLOAD_IDS)
                self.assertIsInstance(run["run_id"], str)
                self.assertIsInstance(run["success"], bool)
                metrics = run["metrics"]
                self.assertIsInstance(metrics, dict)
                for key, value in metrics.items():
                    # All metric values must be numbers
                    self.assertIsInstance(value, (int, float), f"Metric {key} must be numeric")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
