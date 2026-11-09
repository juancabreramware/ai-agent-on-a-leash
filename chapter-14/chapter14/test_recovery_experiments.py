import unittest

from .baseline_orchestrator import BaselineOrchestrator
from .recovery_orchestrator import RecoveryOrchestrator
from .workloads import get_workload_profiles, make_initial_state_fixture
from .invariants import InvariantsEngine


class TestRecoveryExperiments(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = InvariantsEngine()
        self.profiles = get_workload_profiles()

    def _run_both(self, workload_id: str, seed: int = 123):
        initial = make_initial_state_fixture()
        profile = self.profiles[workload_id]

        b = BaselineOrchestrator(seed=seed)
        t = RecoveryOrchestrator(seed=seed)

        b_state, b_info = b.run_workload(initial, profile)
        t_state, t_info = t.run_workload(initial, profile)
        return (b_state, b_info), (t_state, t_info)

    def test_wl1_nominal_states_match_and_no_violations(self):
        (b_state, _), (t_state, t_info) = self._run_both("WL1_nominal_no_corruption", seed=1)
        # final states should be equal
        self.assertEqual(b_state, t_state)
        ok_b, errs_b = self.engine.describe_violations(b_state)
        ok_t, errs_t = self.engine.describe_violations(t_state)
        self.assertTrue(ok_b, errs_b)
        self.assertTrue(ok_t, errs_t)
        self.assertFalse(t_info.incident_detected)

    def test_wl2_treatment_detects_corruption(self):
        (b_state, _), (t_state, t_info) = self._run_both(
            "WL2_immediate_corruption_after_safe_start", seed=2
        )
        # baseline should end with violations
        ok_b, errs_b = self.engine.describe_violations(b_state)
        self.assertFalse(ok_b)
        self.assertGreater(len(errs_b), 0)
        # treatment should trigger incident and end with no violations after rollback
        self.assertTrue(t_info.incident_detected)
        ok_t, errs_t = self.engine.describe_violations(t_state)
        self.assertTrue(ok_t, errs_t)

    def test_wl3_late_corruption_treatment_detects(self):
        (b_state, _), (t_state, t_info) = self._run_both(
            "WL3_late_corruption_after_long_run", seed=3
        )
        ok_b, _ = self.engine.describe_violations(b_state)
        self.assertFalse(ok_b)
        self.assertTrue(t_info.incident_detected)
        ok_t, _ = self.engine.describe_violations(t_state)
        self.assertTrue(ok_t)

    def test_wl4_summary_divergence_detected(self):
        (b_state, _), (t_state, t_info) = self._run_both(
            "WL4_hidden_side_effect_external_view", seed=4
        )
        ok_b, _ = self.engine.describe_violations(b_state)
        self.assertFalse(ok_b)
        self.assertTrue(t_info.incident_detected)
        ok_t, _ = self.engine.describe_violations(t_state)
        self.assertTrue(ok_t)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
