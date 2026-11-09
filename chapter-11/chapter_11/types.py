from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal


@dataclass
class Action:
    """Represents a proposed operation.

    Fields mirror the specification:
    - id: stable identifier within a task
    - type: logical operation type, e.g. 'send_email', 'read_file'.
    - resource: target resource or environment, e.g. file path or environment label.
    - payload: arbitrary structured data.
    """

    id: str
    type: str
    resource: str
    payload: Dict[str, object] = field(default_factory=dict)


VerdictLiteral = Literal["APPROVE", "REJECT", "REQUIRE_CHANGE"]


@dataclass
class ActionReview:
    """Supervisor verdict for an action.

    This matches the ActionReview schema in the chapter specification.
    """

    action_id: str
    verdict: VerdictLiteral
    reasons: List[str]
    suggested_fix: Optional[Dict[str, object]] = None
