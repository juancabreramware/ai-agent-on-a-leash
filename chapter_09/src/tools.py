import time
from typing import Dict, Any


# Global in-memory side-effect store used by tests and experiments.
# It is a simple dictionary keyed by tool name, then by action_id.
_SIDE_EFFECT_STORE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "transfer_funds": {},
    "delete_user": {},
    "change_config": {},
    "disable_2fa": {},
    "increase_credit_limit": {},
    "rotate_db_credentials": {},
    "update_email": {},
    "generate_report": {},
    "issue_refund": {},
}


def reset_side_effect_store() -> None:
    for tool_name in list(_SIDE_EFFECT_STORE.keys()):
        _SIDE_EFFECT_STORE[tool_name] = {}


def get_side_effect_store() -> Dict[str, Dict[str, Dict[str, Any]]]:
    return _SIDE_EFFECT_STORE


def _record_effect(tool: str, action_id: str, payload: Dict[str, Any]) -> None:
    store = _SIDE_EFFECT_STORE.setdefault(tool, {})
    store[action_id] = {
        "payload": payload,
        "timestamp": time.time(),
    }


# High-risk tools


def transfer_funds(action_id: str, source: str, dest: str, amount: float) -> None:
    _record_effect(
        "transfer_funds",
        action_id,
        {"source": source, "dest": dest, "amount": amount},
    )


def delete_user(action_id: str, user_id: str) -> None:
    _record_effect("delete_user", action_id, {"user_id": user_id})


def change_config(action_id: str, key: str, value: str) -> None:
    _record_effect("change_config", action_id, {"key": key, "value": value})


def disable_2fa(action_id: str, user_id: str) -> None:
    _record_effect("disable_2fa", action_id, {"user_id": user_id})


def increase_credit_limit(action_id: str, user_id: str, new_limit: float) -> None:
    _record_effect(
        "increase_credit_limit", action_id, {"user_id": user_id, "new_limit": new_limit}
    )


def rotate_db_credentials(action_id: str) -> None:
    _record_effect("rotate_db_credentials", action_id, {})


# Lower-risk tools


def update_email(action_id: str, user_id: str, new_email: str) -> None:
    _record_effect(
        "update_email", action_id, {"user_id": user_id, "new_email": new_email}
    )


def generate_report(action_id: str, period: str) -> None:
    _record_effect("generate_report", action_id, {"period": period})


def issue_refund(action_id: str, user_id: str, amount: float) -> None:
    _record_effect("issue_refund", action_id, {"user_id": user_id, "amount": amount})
