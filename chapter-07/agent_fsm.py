from typing import Dict, Any, List

from tools import MockTools, MockLLM
from fsm_definition import FSMDefinition


class FSMAgent:
    """Treatment agent orchestrated via a deterministic FSM.

    The FSM restricts which tools can be called and in which order.
    Guard predicates must pass before transitions occur.
    """

    def __init__(self, tools: MockTools, llm: MockLLM, max_steps: int = 10) -> None:
        self.tools = tools
        self.llm = llm
        self.max_steps = max_steps
        self.fsm = FSMDefinition()

    def run(self, workload_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        history: List[Dict[str, Any]] = []
        steps = 0
        invalid_tool_calls = 0
        ctx: Dict[str, Any] = {}

        state = self.fsm.initial_state(workload_id)

        while steps < self.max_steps and not self.fsm.is_terminal(workload_id, state):
            allowed_tools = self.fsm.allowed_tools(workload_id, state)
            transitions = self.fsm.allowed_transitions(workload_id, state)
            transition_names = [t.name for t in transitions]

            decision = self.llm.decide_fsm_action(
                step_index=steps,
                history=history,
                state=state,
                allowed_transitions=transition_names,
                allowed_tools=allowed_tools,
                workload_id=workload_id,
            )
            steps += 1

            # Handle tool call under FSM constraints
            if decision.get("type") == "tool":
                tool_name = decision.get("name")
                if tool_name not in allowed_tools:
                    invalid_tool_calls += 1
                    history.append(
                        {
                            "event": "invalid_tool",
                            "state": state,
                            "name": tool_name,
                        }
                    )
                else:
                    args = decision.get("args", {})
                    result = self._dispatch_tool(workload_id, tool_name, args, payload)
                    # Update context for guards
                    if workload_id == "wf-1":
                        if tool_name == "read_document":
                            ctx["parsed_document"] = result.result
                        elif tool_name == "write_summary":
                            ctx["summary"] = result.result.get("summary")
                    else:
                        if tool_name == "load_sample_rows":
                            ctx["sample_rows"] = result.result.get("rows")
                        elif tool_name == "propose_transforms":
                            ctx["plan_steps"] = result.result.get("steps")
                        elif tool_name == "submit_change_request":
                            ctx["change_request_id"] = result.result.get("request_id")

                    history.append(
                        {
                            "event": "tool",
                            "state": state,
                            "name": tool_name,
                            "result": result.result,
                        }
                    )

            # Handle transition with guards
            if "transition" in decision:
                chosen_name = decision["transition"]
                t_map = {t.name: t for t in transitions}
                if chosen_name in t_map:
                    t = t_map[chosen_name]
                    guards_ok = all(g(ctx) for g in t.guards)
                    history.append(
                        {
                            "event": "transition_attempt",
                            "from": state,
                            "to": t.target,
                            "name": t.name,
                            "guards_ok": guards_ok,
                        }
                    )
                    if guards_ok:
                        state = t.target
                else:
                    history.append(
                        {
                            "event": "transition_invalid",
                            "from": state,
                            "name": chosen_name,
                        }
                    )

        completed = self.fsm.is_terminal(workload_id, state)

        return {
            "history": history,
            "steps": steps,
            "invalid_tool_calls": invalid_tool_calls,
            "completed": completed,
            "final_state": state,
        }

    def _dispatch_tool(
        self,
        workload_id: str,
        name: str,
        args: Dict[str, Any],
        payload: Dict[str, Any],
    ):
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
