from dataclasses import dataclass
from typing import Dict, List, Callable, Any


@dataclass
class Transition:
    name: str
    target: str
    guards: List[Callable[[Dict[str, Any]], bool]]


@dataclass
class StateDef:
    name: str
    allowed_tools: List[str]
    transitions: List[Transition]
    terminal: bool = False


class FSMDefinition:
    """Finite state machine for the treatment agent.

    We define a simple linear-ish workflow for both workloads but
    capture them in a single FSM keyed by workload_id.
    """

    def __init__(self) -> None:
        self.states: Dict[str, Dict[str, StateDef]] = {}
        self._build()

    # Guard helpers
    @staticmethod
    def _guard_always(_: Dict[str, Any]) -> bool:
        return True

    @staticmethod
    def _guard_has_field(ctx: Dict[str, Any], field: str) -> bool:
        return bool(ctx.get(field))

    def _build(self) -> None:
        # For wf-1: COLLECT -> SEARCH -> DRAFT -> FINALIZE
        wf1_states: Dict[str, StateDef] = {}

        wf1_states["COLLECT"] = StateDef(
            name="COLLECT",
            allowed_tools=["read_document"],
            transitions=[
                Transition(
                    name="to_search",
                    target="SEARCH",
                    guards=[lambda ctx, f="parsed_document": self._guard_has_field(ctx, f)],
                )
            ],
        )
        wf1_states["SEARCH"] = StateDef(
            name="SEARCH",
            allowed_tools=["search_kb"],
            transitions=[
                Transition(
                    name="to_draft",
                    target="DRAFT",
                    guards=[self._guard_always],
                )
            ],
        )
        wf1_states["DRAFT"] = StateDef(
            name="DRAFT",
            allowed_tools=["write_summary"],
            transitions=[
                Transition(
                    name="to_finalize",
                    target="FINALIZE",
                    guards=[lambda ctx, f="summary": self._guard_has_field(ctx, f)],
                )
            ],
        )
        wf1_states["FINALIZE"] = StateDef(
            name="FINALIZE", allowed_tools=[], transitions=[], terminal=True
        )

        self.states["wf-1"] = wf1_states

        # For wf-2: INSPECT -> PLAN -> REQUEST -> DONE
        wf2_states: Dict[str, StateDef] = {}

        wf2_states["INSPECT"] = StateDef(
            name="INSPECT",
            allowed_tools=["load_sample_rows"],
            transitions=[
                Transition(
                    name="to_plan",
                    target="PLAN",
                    guards=[lambda ctx, f="sample_rows": self._guard_has_field(ctx, f)],
                )
            ],
        )
        wf2_states["PLAN"] = StateDef(
            name="PLAN",
            allowed_tools=["propose_transforms"],
            transitions=[
                Transition(
                    name="to_request",
                    target="REQUEST",
                    guards=[lambda ctx, f="plan_steps": self._guard_has_field(ctx, f)],
                )
            ],
        )
        wf2_states["REQUEST"] = StateDef(
            name="REQUEST",
            allowed_tools=["submit_change_request"],
            transitions=[
                Transition(
                    name="to_done",
                    target="DONE",
                    guards=[lambda ctx, f="change_request_id": self._guard_has_field(ctx, f)],
                )
            ],
        )
        wf2_states["DONE"] = StateDef(
            name="DONE", allowed_tools=[], transitions=[], terminal=True
        )

        self.states["wf-2"] = wf2_states

    def initial_state(self, workload_id: str) -> str:
        if workload_id == "wf-1":
            return "COLLECT"
        return "INSPECT"

    def get_state(self, workload_id: str, state_name: str) -> StateDef:
        return self.states[workload_id][state_name]

    def is_terminal(self, workload_id: str, state_name: str) -> bool:
        return self.get_state(workload_id, state_name).terminal

    def allowed_tools(self, workload_id: str, state_name: str) -> List[str]:
        return list(self.get_state(workload_id, state_name).allowed_tools)

    def allowed_transitions(self, workload_id: str, state_name: str) -> List[Transition]:
        return list(self.get_state(workload_id, state_name).transitions)
