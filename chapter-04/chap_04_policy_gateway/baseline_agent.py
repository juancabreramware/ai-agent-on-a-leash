from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Callable

from .audit import AuditEntry, InMemoryAuditor
from .tools import build_tool_registry
from .workloads import WorkloadCase, plan_for_workload


@dataclass
class BaselineRunResult:
    executed: bool
    error: str | None
    elapsed_ms: float


class BaselineAgent:
    """Simple tool-using agent with no policy enforcement.

    It accepts a workload, obtains a deterministic proposed action via
    `plan_for_workload`, and directly calls the underlying tool if the
    arguments are syntactically valid.
    """

    def __init__(self, auditor: InMemoryAuditor | None = None) -> None:
        self.tools: Dict[str, Callable[..., Any]] = build_tool_registry()
        self.auditor = auditor or InMemoryAuditor()

    def run_workload(self, workload: WorkloadCase) -> BaselineRunResult:
        proposed = plan_for_workload(workload)
        tool = self.tools.get(proposed.tool_name)
        start = time.perf_counter()
        executed = False
        error: str | None = None
        try:
            if tool is None:
                error = f"Unknown tool: {proposed.tool_name}"
            else:
                # Minimal syntactic validation: ensure args is a dict
                if not isinstance(proposed.args, dict):
                    error = "Invalid args; expected dict"
                else:
                    tool(**proposed.args)
                    executed = True
        except Exception as exc:  # pragma: no cover - unexpected path
            error = repr(exc)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Baseline has no real policies; for schema compatibility, we record
        # a pseudo-policy_id and mark policy_effect as not_applicable.
        entry = AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            variant="baseline",
            workload_id=workload.id,
            tool_name=proposed.tool_name,
            action_context={"workload_context": workload.context, **proposed.args},
            decision="allow" if executed and error is None else "deny",
            policy_id="baseline_no_policy",
            policy_effect="not_applicable",
            decision_latency_ms=elapsed_ms,
            executed=executed,
            error=error,
        )
        self.auditor.record(entry)

        return BaselineRunResult(executed=executed, error=error, elapsed_ms=elapsed_ms)
