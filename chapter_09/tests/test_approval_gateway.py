import time
import unittest

from src.approval_gateway import ApprovalGateway
from src.pending_store import PendingActionStore, ActionState
from src.risk_scoring import RiskScorer
from src.human_simulator import HumanApproverConfig, HumanApprover
from src.tools import (
    reset_side_effect_store,
    get_side_effect_store,
    transfer_funds,
    generate_report,
)


class TestApprovalGateway(unittest.TestCase):
    def setUp(self) -> None:
        reset_side_effect_store()
        self.store = PendingActionStore()
        self.risk_scorer = RiskScorer()

    def _make_gateway(self, human_mode: str, delay: float, timeout: float) -> ApprovalGateway:
        human_cfg = HumanApproverConfig(mode=human_mode, delay_seconds=delay)
        human = HumanApprover(self.store, human_cfg)

        def callback(action_id: str) -> None:
            human.process(action_id)

        tools = {"transfer_funds": transfer_funds, "generate_report": generate_report}
        return ApprovalGateway(
            store=self.store,
            risk_scorer=self.risk_scorer,
            tools=tools,
            approve_callback=callback,
            timeout_seconds=timeout,
        )

    def test_low_risk_bypass(self) -> None:
        gw = self._make_gateway("approve", 0.0, 1.0)
        result = gw.submit_and_wait("generate_report", period="last_week")
        self.assertEqual(result.status, "bypassed")
        store = get_side_effect_store()["generate_report"]
        self.assertEqual(len(store), 1)

    def test_high_risk_approved_executes_once(self) -> None:
        gw = self._make_gateway("approve", 0.0, 1.0)
        result = gw.submit_and_wait("transfer_funds", source="A", dest="B", amount=1.0)
        self.assertEqual(result.status, "executed")
        actions = list(self.store.items())
        self.assertEqual(len(actions), 1)
        action_id, action = actions[0]
        self.assertEqual(action.state, ActionState.EXECUTED)
        tool_store = get_side_effect_store()["transfer_funds"]
        self.assertIn(action_id, tool_store)

    def test_high_risk_denied_never_executes(self) -> None:
        gw = self._make_gateway("deny", 0.0, 1.0)
        result = gw.submit_and_wait("transfer_funds", source="A", dest="B", amount=1.0)
        self.assertEqual(result.status, "denied")
        actions = list(self.store.items())
        self.assertEqual(len(actions), 1)
        _, action = actions[0]
        self.assertEqual(action.state, ActionState.DENIED)
        self.assertEqual(len(get_side_effect_store()["transfer_funds"]), 0)

    def test_timeout_marks_timeout_and_no_execution(self) -> None:
        # Ignore mode with short timeout; callback does nothing.
        gw = self._make_gateway("ignore", 0.0, 0.0)
        result = gw.submit_and_wait("transfer_funds", source="A", dest="B", amount=1.0)
        self.assertEqual(result.status, "timeout")
        actions = list(self.store.items())
        self.assertEqual(len(actions), 1)
        _, action = actions[0]
        self.assertEqual(action.state, ActionState.TIMEOUT)
        self.assertEqual(len(get_side_effect_store()["transfer_funds"]), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
