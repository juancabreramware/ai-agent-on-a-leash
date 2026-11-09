from typing import List, Dict, Any

from tools import MockTools, MockLLM


class FreeformAgent:
    """Baseline agent: free-form loop with no explicit FSM.

    The agent uses MockLLM to decide which tool to call next (if any)
    and continues until a final answer or max_steps is reached.
    """

    def __init__(self, tools: MockTools, llm: MockLLM, max_steps: int = 10) -> None:
        self.tools = tools
        self.llm = llm
        self.max_steps = max_steps

    def run(self, workload_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        history: List[Dict[str, Any]] = []
        steps = 0
        invalid_tool_calls = 0
        completed = False

        if workload_id.startswith("wf-1"):
            available_tools = ["read_document", "search_kb", "write_summary"]
        else:
            available_tools = ["load_sample_rows", "propose_transforms", "submit_change_request"]

        while steps < self.max_steps and not completed:
            decision = self.llm.decide_freeform_action(
                step_index=steps,
                history=history,
                available_tools=available_tools,
                workload_id=workload_id,
            )
            steps += 1

            if decision.get("type") == "final":
                completed = True
                history.append({"type": "final", "content": decision.get("content", "")})
                break

            if decision.get("type") == "tool":
                tool_name = decision.get("name")
                args = decision.get("args", {})
                if tool_name not in available_tools:
                    invalid_tool_calls += 1
                    history.append({"type": "invalid_tool", "name": tool_name, "args": args})
                    continue

                result = self._dispatch_tool(workload_id, tool_name, args, payload)
                history.append({"type": "tool", "name": tool_name, "args": args, "result": result.result})
            else:
                history.append({"type": "noop"})

        return {
            "history": history,
            "steps": steps,
            "invalid_tool_calls": invalid_tool_calls,
            "completed": completed,
        }

    def _dispatch_tool(
        self,
        workload_id: str,
        name: str,
        args: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Any:
        # Wire tools to workloads explicitly
        if workload_id.startswith("wf-1"):
            if name == "read_document":
                return self.tools.read_document(payload["document"])
            if name == "search_kb":
                return self.tools.search_kb(args.get("query", ""))
            if name == "write_summary":
                return self.tools.write_summary(args.get("fields", {}))
        else:
            if name == "load_sample_rows":
                return self.tools.load_sample_rows(payload["schema"])
            if name == "propose_transforms":
                return self.tools.propose_transforms(payload["issue"])
            if name == "submit_change_request":
                return self.tools.submit_change_request(args.get("plan", []))
        raise ValueError(f"Unknown tool {name}")
