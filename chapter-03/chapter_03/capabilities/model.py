from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal


CapabilityType = Literal[
    "read_file",
    "write_file",
    "transfer_funds",
    "list_users",
]


@dataclass
class Principal:
    principal_id: str


@dataclass
class ReadFileScope:
    allowed_prefixes: List[str]


@dataclass
class WriteFileScope:
    allowed_prefixes: List[str]


@dataclass
class TransferFundsScope:
    from_accounts: List[str]
    to_accounts: List[str]
    max_amount_per_call: float
    allowed_currency: str


@dataclass
class ListUsersScope:
    read_only: bool = True


@dataclass
class Capability:
    capability_id: str
    principal_id: str
    type: CapabilityType
    scope: object


def capability_to_dict(cap: Capability) -> Dict[str, object]:
    """Simple serialization helper used only in debugging if needed."""
    return {
        "capability_id": cap.capability_id,
        "principal_id": cap.principal_id,
        "type": cap.type,
        "scope": cap.scope.__dict__,
    }
