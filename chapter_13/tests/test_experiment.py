import json
import os
import unittest

import run as experiment_run
from context_tokens import ContextToken
from memory_baseline import BaselineMemoryStore, text_search
from policies import (
    SENSITIVITY_NORMAL,
    SENSITIVITY_PII,
    SENSITIVITY_SECRET,
    AccessPolicy,
)
from scoped_memory import ScopedMemoryStore
from vector_adapter_mock import ScopedVectorAdapter, ToyVectorIndex


class TestBaselineVsTreatmentWL1(unittest.TestCase):
    def test_wl1_behavior(self) -> None:
        runs = experiment_run.run_wl1_cross_task_private_leak()
        self.assertEqual(len(runs), 2)

        baseline = next(r for r in runs if r["variant"] == "baseline")
        treatment = next(r for r in runs if r["variant"] == "treatment")

        # Baseline should leak in at least one of the broad queries.
        self.assertGreater(baseline["metrics"]["cross_scope_leak_successes"], 0.0)
        # Treatment should perform multiple leak attempts mirroring baseline intent
        # but must not succeed in any of them.
        self.assertEqual(treatment["metrics"]["cross_scope_leak_attempts"], 3.0)
        self.assertEqual(treatment["metrics"]["cross_scope_leak_successes"], 0.0)
        self.assertTrue(baseline["success"])
        self.assertTrue(treatment["success"])


class TestRedactionWL2(unittest.TestCase):
    def test_wl2_behavior(self) -> None:
        runs = experiment_run.run_wl2_redaction_within_allowed_scope()
        self.assertEqual(len(runs), 2)

        baseline = next(r for r in runs if r["variant"] == "baseline")
        treatment = next(r for r in runs if r["variant"] == "treatment")

        # Baseline: has required items but no redaction
        self.assertGreaterEqual(baseline["metrics"]["redaction_required_items"], 1.0)
        self.assertEqual(baseline["metrics"]["redaction_applied_items"], 0.0)
        # Unauthorized / FP denials should be zero and explicitly measured.
        self.assertEqual(baseline["metrics"]["unauthorized_access_denied"], 0.0)
        self.assertEqual(baseline["metrics"]["false_positive_denials"], 0.0)

        # Treatment: all required items must be redacted for agent role
        self.assertGreaterEqual(treatment["metrics"]["redaction_required_items"], 1.0)
        self.assertEqual(
            treatment["metrics"]["redaction_required_items"],
            treatment["metrics"]["redaction_applied_items"],
        )
        # And it should not spuriously deny legitimate accesses.
        self.assertEqual(treatment["metrics"]["unauthorized_access_denied"], 0.0)
        self.assertEqual(treatment["metrics"]["false_positive_denials"], 0.0)
        self.assertTrue(treatment["success"])


class TestSharedVsPrivateWL3(unittest.TestCase):
    def test_wl3_behavior(self) -> None:
        runs = experiment_run.run_wl3_shared_vs_private_scopes()
        self.assertEqual(len(runs), 2)
        baseline = next(r for r in runs if r["variant"] == "baseline")
        treatment = next(r for r in runs if r["variant"] == "treatment")

        # Baseline expected to leak across private scopes
        self.assertGreater(baseline["metrics"]["cross_scope_leak_successes"], 0.0)

        # Treatment: same number of attempts but no cross-scope leaks.
        self.assertEqual(treatment["metrics"]["cross_scope_leak_attempts"], 3.0)
        self.assertEqual(treatment["metrics"]["cross_scope_leak_successes"], 0.0)

        # Shared retrievals should work in both
        self.assertEqual(
            baseline["metrics"]["allowed_shared_retrievals"],
            treatment["metrics"]["allowed_shared_retrievals"],
        )

        self.assertTrue(baseline["success"])
        self.assertTrue(treatment["success"])


class TestVectorAdapterWL4(unittest.TestCase):
    def test_wl4_behavior(self) -> None:
        runs = experiment_run.run_wl4_vector_store_adaptor_smoke_test()
        self.assertEqual(len(runs), 2)
        baseline = next(r for r in runs if r["variant"] == "baseline")
        treatment = next(r for r in runs if r["variant"] == "treatment")

        # Baseline: both queries return something
        self.assertGreaterEqual(baseline["metrics"]["results_query1"], 1.0)
        self.assertGreaterEqual(baseline["metrics"]["results_query2"], 1.0)

        # Treatment: scoping enforced; success flag already checks detailed conditions
        self.assertTrue(treatment["success"])


class TestEvidenceSchema(unittest.TestCase):
    def test_run_py_writes_valid_evidence(self) -> None:
        # Ensure the evidence directory exists and is writable
        evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        os.makedirs(evidence_dir, exist_ok=True)

        # Remove any existing file to avoid confusion
        path = os.path.join(evidence_dir, "results.json")
        if os.path.exists(path):
            os.remove(path)

        # Execute main (in-process) to create evidence
        experiment_run.main()

        self.assertTrue(os.path.exists(path))

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level checks
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("chapter"), 13)
        self.assertEqual(data.get("experiment_id"), "chap13-secure-memory-context-mgmt-v1")

        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        # We expect exactly 2 variants per workload across 4 workloads
        self.assertGreaterEqual(len(runs), 8)

        # Track workload / variant coverage
        workload_variants = {}

        # Track that at least one metric key is shared across all runs
        per_run_metric_keys = []

        for run in runs:
            self.assertIn("variant", run)
            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIsInstance(run["success"], bool)

            key = (run["workload_id"], run["variant"])
            workload_variants[key] = True

            metrics = run.get("metrics")
            self.assertIsInstance(metrics, dict)
            # Evidence must provide at least one numeric metric per run
            self.assertGreaterEqual(len(metrics), 1, msg="Each run must include at least one numeric metric.")
            # All metric values must be numeric
            for k, v in metrics.items():
                self.assertIsInstance(v, (int, float), msg=f"Metric {k} is not numeric: {v}")

            per_run_metric_keys.append(set(metrics.keys()))

        # Ensure at least one baseline and one treatment per workload
        workload_ids = {run["workload_id"] for run in runs}
        for wid in workload_ids:
            self.assertIn((wid, "baseline"), workload_variants)
            self.assertIn((wid, "treatment"), workload_variants)

        # Ensure there is at least one shared numeric metric name across *all* runs
        shared_keys = set.intersection(*per_run_metric_keys) if per_run_metric_keys else set()
        self.assertIn("cross_scope_leak_attempts", shared_keys)


class TestCoreComponents(unittest.TestCase):
    def test_baseline_store_simple(self) -> None:
        store = BaselineMemoryStore()
        store.write_memory("t1", "hello", {"k": "v"})
        all_items = store.read_memory()
        self.assertEqual(len(all_items), 1)
        self.assertEqual(all_items[0]["content"], "hello")

        filtered = store.read_memory({"k": "v"})
        self.assertEqual(len(filtered), 1)

        search = text_search(store, "hello")
        self.assertEqual(len(search), 1)

    def test_scoped_store_isolation(self) -> None:
        store = ScopedMemoryStore()
        tenant_id = "t"
        ctx1 = ContextToken.create("task1", tenant_id, "agent", {f"tenant:{tenant_id}:task1"})
        ctx2 = ContextToken.create("task2", tenant_id, "agent", {f"tenant:{tenant_id}:task2"})

        store.write(ctx1, {"kind": "note", "text": "hello from 1"}, sensitivity=SENSITIVITY_NORMAL)
        store.write(ctx2, {"kind": "note", "text": "hello from 2"}, sensitivity=SENSITIVITY_NORMAL)

        r1 = store.query(ctx1, {"kind": "note"})
        r2 = store.query(ctx2, {"kind": "note"})

        self.assertEqual(len(r1), 1)
        self.assertEqual(len(r2), 1)
        self.assertNotEqual(r1[0]["text"], r2[0]["text"])

    def test_access_policy_redaction_flag(self) -> None:
        ctx_agent = ContextToken.create("t1", "tenant", "agent", {"s1"})
        ctx_auditor = ContextToken.create("t1", "tenant", "auditor", {"s1"})

        # Agent should need redaction for PII, auditor not.
        self.assertTrue(AccessPolicy.needs_redaction(ctx_agent, SENSITIVITY_PII))
        self.assertFalse(AccessPolicy.needs_redaction(ctx_auditor, SENSITIVITY_PII))

    def test_vector_adapter_scoping(self) -> None:
        idx = ToyVectorIndex()
        idx.add("d1", "text A", "s1")
        idx.add("d2", "text B", "s2")
        adapter = ScopedVectorAdapter(idx)

        ctx = ContextToken.create("task", "tenant", "agent", {"s1"})
        res = adapter.search_scoped(ctx, "text", k=5)
        ids = {r["doc_id"] for r in res}
        self.assertIn("d1", ids)
        self.assertNotIn("d2", ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
