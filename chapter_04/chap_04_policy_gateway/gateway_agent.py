from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Callable

from .audit import AuditEntry, InMemoryAuditor
from .decision_engine import DecisionEngine
from .tools import build_tool_registry
from .workloads import WorkloadCase, plan_for_workload


@dataclass
class GatewayRunResult:
    executed: bool
    error: str | None
    elapsed_ms: float


class PolicyInterceptor:
    """Wraps a tool registry and mediates all tool invocations via policies."""

    def __init__(self, decision_engine: DecisionEngine, auditor: InMemoryAuditor) -> None:
        self.tools: Dict[str, Callable[..., Any]] = build_tool_registry()
        self.engine = decision_engine
        self.auditor = auditor

    def call_tool(
        self,
        workload_id: str,
        variant: str,
        tool_name: str,
        ctx: Dict[str, Any],
        args: Dict[str, Any],
    ) -> tuple[bool, str | None, float]:
        # Build action context for decision engine
        action_ctx = {**ctx, **args, "tool_name": tool_name}
        decision = self.engine.decide(action_ctx)
        executed = False
        error: str | None = None
        tool = self.tools.get(tool_name)
        execution_start = time.perf_counter()
        if decision.effect == "allow" and tool is not None:
            try:
                tool(**args)
                executed = True
            except Exception as exc:  # pragma: no cover - unexpected path
                error = repr(exc)
        elif tool is None:
            error = f"Unknown tool: {tool_name}"

        elapsed_ms = (time.perf_counter() - execution_start) * 1000.0

        entry = AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            variant=variant,
            workload_id=workload_id,
            tool_name=tool_name,
            action_context=action_ctx,
            decision=decision.effect,
            policy_id=decision.policy_id,
            policy_effect=decision.policy_effect,
            decision_latency_ms=decision.latency_ms,
            executed=executed,
            error=error,
        )
        self.auditor.record(entry)

        return executed, error, elapsed_ms


class GatewayAgent:
    """Agent that routes all tool invocations through a policy gateway."""

    def __init__(self, auditor: InMemoryAuditor | None = None) -> None:
        self.auditor = auditor or InMemoryAuditor()
        self.engine = DecisionEngine()
        self.interceptor = PolicyInterceptor(self.engine, self.auditor)

    def run_workload(self, workload: WorkloadCase) -> GatewayRunResult:
        proposed = plan_for_workload(workload)
        start = time.perf_counter()
        executed, error, _ = self.interceptor.call_tool(
            workload_id=workload.id,
            variant="gateway",
            tool_name=proposed.tool_name,
            ctx=workload.context,
            args=proposed.args,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return GatewayRunResult(executed=executed, error=error, elapsed_ms=elapsed_ms)
