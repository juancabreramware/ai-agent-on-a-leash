import random
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


@dataclass
class ToolResult:
    name: str
    args: Dict[str, Any]
    result: Dict[str, Any]


class MockTools:
    """Deterministic mock tools shared by baseline and treatment.

    Tools are intentionally simple and side-effect-free to keep the
    experiment fast and reproducible in a sandboxed environment.
    """

    def __init__(self, seed: int = 0) -> None:
        self.random = random.Random(seed)

    # Workload wf-1 tools
    def read_document(self, content: str) -> ToolResult:
        # Simple parsing: count lines and extract first non-empty line as title
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        title = lines[0][:50] if lines else "Untitled incident"
        severity = "high" if "SEV-1" in content or "SEV1" in content else "medium"
        impact = "users affected" if "users" in content.lower() else "unknown"
        return ToolResult(
            name="read_document",
            args={"len": len(content)},
            result={
                "title": title,
                "severity": severity,
                "user_impact": impact,
            },
        )

    def search_kb(self, query: str) -> ToolResult:
        # Deterministic pseudo search using hash of query
        h = abs(hash(query)) % 3
        if h == 0:
            matches = []
        elif h == 1:
            matches = ["INC-101 similar outage"]
        else:
            matches = ["INC-202 partial outage", "INC-303 latency spike"]
        return ToolResult(
            name="search_kb", args={"query": query}, result={"matches": matches}
        )

    def write_summary(self, fields: Dict[str, Any]) -> ToolResult:
        # Join fields into a single string summary
        summary = f"[{fields.get('severity','?').upper()}] {fields.get('title','Untitled')} - {fields.get('user_impact','impact unknown')}"
        return ToolResult(
            name="write_summary", args={"fields_keys": list(fields.keys())}, result={"summary": summary}
        )

    # Workload wf-2 tools
    def load_sample_rows(self, schema: Dict[str, str]) -> ToolResult:
        # Generate deterministic fake rows based on schema keys
        rows: List[Dict[str, Any]] = []
        for i in range(3):
            row = {k: f"{k}_val_{i}" for k in schema.keys()}
            rows.append(row)
        return ToolResult(
            name="load_sample_rows", args={"schema_keys": list(schema.keys())}, result={"rows": rows}
        )

    def propose_transforms(self, issue: str) -> ToolResult:
        steps: List[str]
        if "null" in issue.lower() or "missing" in issue.lower():
            steps = ["Identify columns with nulls", "Fill with default or drop rows"]
        else:
            steps = ["Detect type inconsistencies", "Normalize types", "Handle outliers"]
        return ToolResult(
            name="propose_transforms", args={"issue": issue}, result={"steps": steps}
        )

    def submit_change_request(self, plan: List[str]) -> ToolResult:
        # Return a deterministic ID based on plan length
        request_id = f"CR-{len(plan):03d}"
        return ToolResult(
            name="submit_change_request", args={"steps_count": len(plan)}, result={"request_id": request_id}
        )


class MockLLM:
    """Deterministic mock 'LLM' used by agents.

    Instead of real language understanding, we:
    - Inspect the current step index and simple flags.
    - Emit an action dict indicating 'tool' / 'final' and which tool to use.

    This preserves the *shape* of an LLM-driven loop while remaining
    fast and offline.
    """

    def __init__(self, seed: int = 0) -> None:
        self.random = random.Random(seed)

    def decide_freeform_action(
        self,
        step_index: int,
        history: List[Dict[str, Any]],
        available_tools: List[str],
        workload_id: str,
    ) -> Dict[str, Any]:
        """Decision policy for baseline agent.

        Simple heuristics to exercise invalid / out-of-order behavior:
        - Sometimes calls a random tool even if semantically odd.
        - Stops after a small number of steps.
        """

        # Terminate early with some probability or after 5 steps
        if step_index >= 5 or (step_index >= 2 and self.random.random() < 0.2):
            return {"type": "final", "content": "Done"}

        # Choose a tool heuristically, but allow odd choices
        if workload_id.startswith("wf-1"):
            # occasionally misuse search_kb first
            if step_index == 0 and "search_kb" in available_tools:
                return {"type": "tool", "name": "search_kb", "args": {"query": "incident"}}
            # otherwise cycle through tools
            name = available_tools[step_index % len(available_tools)]
            args = {"content": "dummy"} if name == "read_document" else {"query": "incident"}
            if name == "write_summary":
                args = {"fields": {"title": "t", "severity": "s", "user_impact": "u"}}
            return {"type": "tool", "name": name, "args": args}

        # wf-2
        if workload_id.startswith("wf-2"):
            if step_index == 0 and "submit_change_request" in available_tools:
                # This is intentionally out-of-order for baseline
                return {"type": "tool", "name": "submit_change_request", "args": {"plan": ["skip"]}}
            name = available_tools[step_index % len(available_tools)]
            if name == "load_sample_rows":
                args = {"schema": {"col1": "str"}}
            elif name == "propose_transforms":
                args = {"issue": "missing values"}
            else:
                args = {"plan": ["step1", "step2"]}
            return {"type": "tool", "name": name, "args": args}

        return {"type": "final", "content": "Done"}

    def decide_fsm_action(
        self,
        step_index: int,
        history: List[Dict[str, Any]],
        state: str,
        allowed_transitions: List[str],
        allowed_tools: List[str],
        workload_id: str,
    ) -> Dict[str, Any]:
        """Decision policy for FSM agent.

        The mock model chooses:
        - A transition (if any are available), preferring forward progression.
        - An allowed tool, if appropriate for the state.
        """

        action: Dict[str, Any] = {"type": "noop"}

        # Simple deterministic progression: pick the lexicographically last transition
        transition_name = allowed_transitions[-1] if allowed_transitions else None
        if transition_name:
            action["transition"] = transition_name

        # Choose a tool allowed in this state based on workload
        if allowed_tools:
            if workload_id.startswith("wf-1"):
                # Prefer read_document then search_kb then write_summary
                for preferred in ["read_document", "search_kb", "write_summary"]:
                    if preferred in allowed_tools:
                        tool_name = preferred
                        break
                else:
                    tool_name = allowed_tools[0]
            else:
                for preferred in ["load_sample_rows", "propose_transforms", "submit_change_request"]:
                    if preferred in allowed_tools:
                        tool_name = preferred
                        break
                else:
                    tool_name = allowed_tools[0]

            if tool_name == "read_document":
                args = {"content": "dummy"}
            elif tool_name == "search_kb":
                args = {"query": "incident"}
            elif tool_name == "write_summary":
                args = {"fields": {"title": "t", "severity": "s", "user_impact": "u"}}
            elif tool_name == "load_sample_rows":
                args = {"schema": {"col1": "str"}}
            elif tool_name == "propose_transforms":
                args = {"issue": "missing values"}
            else:  # submit_change_request
                args = {"plan": ["step1", "step2"]}
            action["type"] = "tool"
            action["name"] = tool_name
            action["args"] = args
        else:
            action["type"] = "final"
            action["content"] = "Done"

        return action
