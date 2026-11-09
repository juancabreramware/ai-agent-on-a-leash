from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    timestamp: str
    variant: str
    workload_id: str
    tool_name: str
    action_context: Dict[str, Any]
    decision: str
    policy_id: str
    policy_effect: str
    decision_latency_ms: float
    executed: bool
    error: Optional[str]


class InMemoryAuditor:
    """Collects audit events in memory.

    This is intentionally simple; callers are responsible for persisting logs
    if desired. Tests and experiment runner can inspect .entries.
    """

    def __init__(self) -> None:
        self.entries: List[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def to_json_lines(self) -> str:
        return "\n".join(json.dumps(asdict(e), sort_keys=True) for e in self.entries)
