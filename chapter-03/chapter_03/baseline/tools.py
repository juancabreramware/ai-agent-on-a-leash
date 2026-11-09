from __future__ import annotations

import os
from typing import Dict, List

from chapter_03.environment import (
    REPORTS_DIR,
    KB_DIR,
    LOGS_DIR,
    PUBLIC_DIR,
    SECRETS_DIR,
    EnvironmentState,
)


def _read_file_generic(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_file(path: str) -> str:
    """Unconstrained file read: any path is allowed if it exists."""
    return _read_file_generic(path)


def write_file_unrestricted(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def transfer_funds_unrestricted(state: EnvironmentState, from_account: str, to_account: str, amount: float) -> bool:
    """Transfer funds without any per-agent authorization.

    Fails only if accounts are missing or balance is insufficient.
    """
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if from_account not in state.accounts or to_account not in state.accounts:
        raise KeyError("unknown account")
    if state.accounts[from_account] < amount:
        return False
    state.accounts[from_account] -= amount
    state.accounts[to_account] += amount
    return True


def list_users(state: EnvironmentState) -> List[str]:
    return list(state.users)


def delete_user(state: EnvironmentState, username: str) -> bool:
    if username in state.users:
        state.users.remove(username)
        return True
    return False


# Convenience functions for baseline workloads to avoid importing dirs

def path_reports(filename: str) -> str:
    return os.path.join(REPORTS_DIR, filename)


def path_kb(filename: str) -> str:
    return os.path.join(KB_DIR, filename)


def path_logs(filename: str) -> str:
    return os.path.join(LOGS_DIR, filename)


def path_public(filename: str) -> str:
    return os.path.join(PUBLIC_DIR, filename)


def path_secrets(filename: str) -> str:
    return os.path.join(SECRETS_DIR, filename)
