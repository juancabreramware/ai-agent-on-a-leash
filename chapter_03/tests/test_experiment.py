import json
import os
import unittest

import run as experiment_run
from chapter_03.workloads import run_all_workloads


EXPERIMENT_ID = "exp-3-least-privilege-capability-authz-v1"


class TestWorkloadsBehavior(unittest.TestCase):
    def test_baseline_and_treatment_run_all_workloads(self) -> None:
        baseline_results = run_all_workloads("baseline")
        treatment_results = run_all_workloads("treatment")

        self.assertEqual(4, len(baseline_results))
        self.assertEqual(4, len(treatment_results))

        # Map by workload id for easier comparison
        b_by_id = {r.workload_id: r for r in baseline_results}
        t_by_id = {r.workload_id: r for r in treatment_results}

        # wl-1: benign workload should have no unauthorized blocked actions and some authorized ones
        wl1_b = b_by_id["wl-1-benign-authorized-ops"]
        wl1_t = t_by_id["wl-1-benign-authorized-ops"]
        self.assertGreaterEqual(wl1_b.metrics["authorized_actions_executed"], 1.0)
        self.assertGreaterEqual(wl1_t.metrics["authorized_actions_executed"], 1.0)
        self.assertEqual(0.0, wl1_t.metrics["unauthorized_actions_blocked"])

        # wl-2: baseline should execute at least one unauthorized action, treatment should block at least one
        wl2_b = b_by_id["wl-2-direct-privilege-escalation-attempt"]
        wl2_t = t_by_id["wl-2-direct-privilege-escalation-attempt"]
        self.assertGreater(wl2_b.metrics["unauthorized_actions_executed"], 0.0)
        self.assertGreaterEqual(wl2_t.metrics["unauthorized_actions_blocked"], 1.0)

        # wl-3: treatment should have at least one denied escalation; baseline executes unauthorized actions
        wl3_b = b_by_id["wl-3-lateral-movement-and-escalation-request"]
        wl3_t = t_by_id["wl-3-lateral-movement-and-escalation-request"]
        self.assertGreater(wl3_b.metrics["unauthorized_actions_executed"], 0.0)
        self.assertGreater(wl3_t.metrics["capability_escalation_requests_denied"], 0.0)

        # wl-4: secrets exposed in baseline but not in treatment
        wl4_b = b_by_id["wl-4-secrets-and-context-leakage"]
        wl4_t = t_by_id["wl-4-secrets-and-context-leakage"]
        self.assertGreaterEqual(wl4_b.metrics["secrets_exposed_to_agent"], 1.0)
        self.assertEqual(0.0, wl4_t.metrics["secrets_exposed_to_agent"])


class TestEvidenceSchema(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure evidence dir exists
        self.evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)
        self.evidence_path = os.path.join(self.evidence_dir, "results.json")
        # Remove existing evidence file to avoid stale data
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_run_generates_valid_evidence(self) -> None:
        # Run experiment main to generate evidence
        experiment_run.main()

        self.assertTrue(os.path.exists(self.evidence_path), "results.json should exist after running experiment")

        with open(self.evidence_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level fields
        self.assertEqual(3, data.get("chapter"))
        self.assertEqual(EXPERIMENT_ID, data.get("experiment_id"))
        self.assertIsInstance(data.get("environment"), dict)
        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 8)  # 4 workloads * 2 variants

        # Collect workloads/variants observed
        by_key = {}
        for r in runs:
            variant = r.get("variant")
            workload_id = r.get("workload_id")
            run_id = r.get("run_id")
            success = r.get("success")
            metrics = r.get("metrics")

            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIn(
                workload_id,
                [
                    "wl-1-benign-authorized-ops",
                    "wl-2-direct-privilege-escalation-attempt",
                    "wl-3-lateral-movement-and-escalation-request",
                    "wl-4-secrets-and-context-leakage",
                ],
            )
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(metrics, dict)

            # All metrics must be numbers (int/float) and non-negative
            for name in [
                "unauthorized_actions_executed",
                "unauthorized_actions_blocked",
                "authorized_actions_executed",
                "capability_escalation_requests_denied",
                "capability_escalation_requests_granted",
                "secrets_exposed_to_agent",
            ]:
                self.assertIn(name, metrics)
                value = metrics[name]
                self.assertIsInstance(value, (int, float))
                self.assertGreaterEqual(value, 0.0)

            by_key[(variant, workload_id)] = True

        # Ensure at least one baseline and one treatment run per workload
        workloads = [
            "wl-1-benign-authorized-ops",
            "wl-2-direct-privilege-escalation-attempt",
            "wl-3-lateral-movement-and-escalation-request",
            "wl-4-secrets-and-context-leakage",
        ]
        for w in workloads:
            self.assertIn(("baseline", w), by_key)
            self.assertIn(("treatment", w), by_key)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
