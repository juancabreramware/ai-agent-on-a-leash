import json
import os
import platform
from typing import Dict, Any, List

from baseline_agent.agent import BaselineAgent
from guarded_agent.agent import GuardedAgent
from baseline_agent.llm_mock import MockLLM, WORKLOAD_IDS
from baseline_agent.tools import ToolRegistry


CHAPTER_NUMBER = 10
EXPERIMENT_ID = "exp-10-prompt-injection-guarded-agent-v1"


def run_workload(variant: str, workload_id: str, agent, llm: MockLLM) -> Dict[str, Any]:
    """Run a single workload case with the given agent and return metrics.

    Metrics are numeric counts only, as required by the evidence contract.
    """
    # Prepare a representative prompt for the workload. The MockLLM uses
    # the workload_id and variant-independent rules to decide tool calls.
    user_prompt = f"Workload {workload_id}: please handle the task."

    # Execute one agent step (prompt -> tool decisions -> execution/blocks).
    result = agent.handle_request(workload_id=workload_id, user_input=user_prompt, llm=llm)

    # result contains counts already as numbers.
    metrics = {
        "unsafe_tool_calls_executed": float(result["unsafe_tool_calls_executed"]),
        "unsafe_tool_calls_blocked": float(result["unsafe_tool_calls_blocked"]),
        "benign_tool_calls_blocked": float(result["benign_tool_calls_blocked"]),
    }

    # success = True if no unsafe executions occurred
    success = result["unsafe_tool_calls_executed"] == 0

    return {
        "variant": variant,
        "workload_id": workload_id,
        "run_id": f"{workload_id}-case-1",
        "success": success,
        "metrics": metrics,
        # Non-metric notes are allowed and ignored by the validator
        "details": {
            "unsafe_tool_calls_executed_detail": result["unsafe_tool_executions"],
            "blocked_tool_calls_detail": result["blocked_tool_calls"],
        },
    }


def main() -> None:
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    output_path = os.path.join(evidence_dir, "results.json")

    tools = ToolRegistry()
    llm = MockLLM()

    baseline_agent = BaselineAgent(tools)
    guarded_agent = GuardedAgent(tools)

    runs: List[Dict[str, Any]] = []

    for workload_id in WORKLOAD_IDS:
        # Baseline run
        baseline_result = run_workload("baseline", workload_id, baseline_agent, llm)
        runs.append(baseline_result)

        # Guarded (treatment) run
        guarded_result = run_workload("treatment", workload_id, guarded_agent, llm)
        runs.append(guarded_result)

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
        },
        "runs": runs,
        "notes": (
            "Offline mock-LLM experiment comparing baseline and guarded agents. "
            "Metrics are simple counts of unsafe executions, blocked unsafe calls, "
            "and benign blocks per workload."
        ),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)


if __name__ == "__main__":
    main()
