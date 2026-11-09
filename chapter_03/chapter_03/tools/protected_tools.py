from __future__ import annotations

import os
from typing import List

from chapter_03.environment import EnvironmentState


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def transfer_funds(state: EnvironmentState, from_account: str, to_account: str, amount: float, currency: str) -> bool:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if currency != "USD":
        return False
    if from_account not in state.accounts or to_account not in state.accounts:
        return False
    if state.accounts[from_account] < amount:
        return False
    state.accounts[from_account] -= amount
    state.accounts[to_account] += amount
    return True


def list_users(state: EnvironmentState) -> List[str]:
    return list(state.users)
