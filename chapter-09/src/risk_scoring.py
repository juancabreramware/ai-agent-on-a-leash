from typing import Dict


class RiskScorer:
    """Deterministic risk scorer based on tool name only."""

    TOOL_RISK: Dict[str, str] = {
        # High risk
        "transfer_funds": "high",
        "delete_user": "high",
        "change_config": "high",
        "disable_2fa": "high",
        "increase_credit_limit": "high",
        "rotate_db_credentials": "high",
        # Medium risk
        "issue_refund": "medium",
        "update_email": "medium",
        # Low risk
        "generate_report": "low",
    }

    def score(self, tool_name: str) -> str:
        return self.TOOL_RISK.get(tool_name, "low")
