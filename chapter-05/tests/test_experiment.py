from __future__ import annotations

import json
import os
import unittest
from typing import Any, Dict, List

import run as run_module
from sandbox_runner import WORKLOADS, run_all_workloads, executed_run_to_record, SandboxedToolRunner, SandboxRequest, SandboxPathError


class TestSandboxExperiment(unittest.TestCase):
    def test_run_all_workloads_schema_and_counts(self) -> None:
        executed = run_all_workloads(baseline_timeout=1.0, sandbox_timeout=0.5)
        # Must have two runs per workload: baseline and treatment
        workload_ids = set(WORKLOADS.keys())
        self.assertGreater(len(workload_ids), 0)
        per_workload: Dict[str, Dict[str, int]] = {wid: {"baseline": 0, "treatment": 0} for wid in workload_ids}

        for erun in executed:
            self.assertIn(erun.workload_id, workload_ids)
            self.assertIn(erun.variant, ("baseline", "treatment"))
            per_workload[erun.workload_id][erun.variant] += 1
            rec = executed_run_to_record(erun)
            # Schema checks
            self.assertIn("variant", rec)
            self.assertIn("workload_id", rec)
            self.assertIn("run_id", rec)
            self.assertIn("success", rec)
            self.assertIn("metrics", rec)
            self.assertIsInstance(rec["metrics"], dict)
            # Metrics must be numeric values
            for k, v in rec["metrics"].items():
                self.assertIsInstance(v, (int, float), msg=f"metric {k} must be numeric, got {type(v)}")

        # ensure each workload has at least one baseline and one treatment run
        for wid, counts in per_workload.items():
            self.assertGreaterEqual(counts["baseline"], 1, msg=f"missing baseline for {wid}")
            self.assertGreaterEqual(counts["treatment"], 1, msg=f"missing treatment for {wid}")

    def test_sandbox_blocks_absolute_path_open(self) -> None:
        root = os.path.abspath("test_sandboxes")
        runner = SandboxedToolRunner(sandbox_root=root)
        code = "with open('/etc/hosts', 'r') as f:\n    print(f.read())\n"
        req = SandboxRequest(code=code, timeout_seconds=0.5, sandbox_root=root)
        res = runner.run_in_sandbox(req)
        self.assertFalse(res.success)
        self.assertIn("SandboxPathError", (res.error_type or ""))

    def test_sandbox_allows_relative_file_write(self) -> None:
        root = os.path.abspath("test_sandboxes_rel")
        runner = SandboxedToolRunner(sandbox_root=root)
        code = "with open('note.txt', 'w') as f:\n    f.write('hello from sandbox')\n\nwith open('note.txt', 'r') as f:\n    print(f.read())\n"
        req = SandboxRequest(code=code, timeout_seconds=0.5, sandbox_root=root)
        res = runner.run_in_sandbox(req)
        self.assertTrue(res.success)
        self.assertIn("hello from sandbox", res.stdout)
        # ensure file exists inside sandbox root, not outside
        expected_path = os.path.join(root, "note.txt")
        self.assertTrue(os.path.exists(expected_path))

    def test_sandbox_times_out_infinite_loop(self) -> None:
        root = os.path.abspath("test_sandboxes_loop")
        runner = SandboxedToolRunner(sandbox_root=root)
        code = "while True:\n    pass\n"
        req = SandboxRequest(code=code, timeout_seconds=0.2, sandbox_root=root)
        res = runner.run_in_sandbox(req)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "TimeoutError")

    def test_run_py_writes_evidence_file_with_schema(self) -> None:
        # Set evidence dir to a temporary local folder
        evidence_dir = os.path.abspath("test_evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        os.environ["BOOKMAS_EVIDENCE_DIR"] = evidence_dir

        # Run main to generate evidence
        run_module.main()

        path = os.path.join(evidence_dir, "results.json")
        self.assertTrue(os.path.exists(path), msg="results.json not created")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level schema
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("chapter"), 5)
        self.assertEqual(data.get("experiment_id"), "exp-ch05-sandboxed-execution-v1")
        self.assertIn("environment", data)
        self.assertIn("os", data["environment"])
        self.assertIn("python", data["environment"])
        self.assertIn("runs", data)

        runs: List[Dict[str, Any]] = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)

        # Track workloads per variant
        seen: Dict[str, Dict[str, int]] = {}

        for r in runs:
            self.assertIn("variant", r)
            self.assertIn(r["variant"], ("baseline", "treatment"))
            self.assertIn("workload_id", r)
            wid = r["workload_id"]
            self.assertIn(wid, WORKLOADS)
            self.assertIn("run_id", r)
            self.assertIn("success", r)
            self.assertIn("metrics", r)
            self.assertIsInstance(r["metrics"], dict)
            for mk, mv in r["metrics"].items():
                self.assertIsInstance(mv, (int, float), msg=f"metric {mk} must be numeric, got {type(mv)}")

            seen.setdefault(wid, {"baseline": 0, "treatment": 0})
            seen[wid][r["variant"]] += 1

        for wid, counts in seen.items():
            self.assertGreaterEqual(counts["baseline"], 1, msg=f"no baseline run for {wid}")
            self.assertGreaterEqual(counts["treatment"], 1, msg=f"no treatment run for {wid}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
