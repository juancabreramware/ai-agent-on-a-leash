# Chapter 07 – Deterministic State Machines for Agent Workflows

This directory contains a fully self-contained Python 3.11+ experiment for:

- **Title:** Deterministic State Machines for Agent Workflows  
- **Experiment ID:** `ch07-deterministic-state-machines-vs-free-form-agents`

The goal is to compare a **free-form agent** against a **state-machine-orchestrated agent** on the same workloads, using deterministic mock LLM/tool behavior so the experiment is fully reproducible and safe to run in an offline sandbox.

Key design decisions for this sandboxed version:

- No external dependencies beyond the Python standard library.
- A deterministic mock "LLM" that uses simple rule-based logic and a seeded PRNG instead of network calls.
- Shared mock tools and workloads for both baseline and treatment.
- A minimal yet realistic finite state machine (FSM) implementation, with explicit states, transitions, and guards.
- Experiment runner that logs per-step events and computes basic metrics directly in-process.
- Evidence output written to `/evidence/results.json` following the specified schema.

## Layout

- `agent_freeform.py` – Baseline agent, no explicit FSM. The agent decides actions based on a mock LLM.
- `agent_fsm.py` – Treatment agent, orchestrated via an explicit deterministic FSM.
- `fsm_definition.py` – FSM state/transition definitions and guard logic.
- `tools.py` – Shared mock tools and a deterministic mock LLM.
- `workloads.py` – Workload definitions and deterministic input fixtures.
- `runner.py` – Core experiment runner and log/metric computation utilities.
- `evaluation.py` – Logic for computing per-run metrics from logs (used by `runner.py`).
- `run.py` – Entry point required by the book infrastructure; runs a small experiment and writes `/evidence/results.json`.
- `requirements.txt` – Empty of runtime deps by design (standard library only).
- `tests/test_experiment.py` – Unit tests validating the experiment schema, FSM behavior, and basic metrics.

## Running the Experiment

From this directory:

```bash
python run.py
```

This will:

1. Run a small number of baseline and treatment episodes on both workloads and all variants.
2. Compute simple metrics for each run:
   - `invalid_tool_calls` – number of invalid tool calls in the run.
   - `steps` – total number of reasoning/tool steps.
   - `completed` – 1 if run reached a terminal condition, 0 otherwise.
3. Write an evidence JSON file to `/evidence/results.json` with this structure:

```json
{
  "chapter": 7,
  "experiment_id": "ch07-deterministic-state-machines-vs-free-form-agents",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "wf-1/wf-1a",
      "run_id": "...",
      "success": true,
      "metrics": {
        "invalid_tool_calls": 0,
        "steps": 4,
        "completed": 1
      }
    },
    {
      "variant": "treatment",
      "workload_id": "wf-1/wf-1a",
      "run_id": "...",
      "success": true,
      "metrics": {
        "invalid_tool_calls": 0,
        "steps": 4,
        "completed": 1
      }
    }
  ],
  "notes": "...optional..."
}
```

The exact numeric values will depend on the execution but are fully deterministic for a fixed Python version and random seed.

## Running Tests

Tests are written using the Python `unittest` framework and can be run as:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests check that:

- `/evidence/results.json` is present and has the required schema after running `run.py`.
- Each run record includes numeric metrics and a boolean `success` field.
- At least one baseline and one treatment run exist per workload.
- Certain FSM-internal properties hold (e.g., impossible out-of-order actions in the FSM treatment according to our guard rules).

## What This Experiment Demonstrates

Conceptually, this chapter contrasts two orchestration patterns for agents that use tools:

1. **Baseline (free-form agent):**
   - A simple loop calls the model each step with conversation history and a list of tools.
   - The model emits an action like `call_tool: "read_document"` or `finish`.
   - Any syntactically valid tool call is accepted.
   - No explicit workflow states or deterministic transition table exist.
   - Logs are just a sequence of messages and tool calls.

2. **Treatment (FSM-constrained agent):**
   - The workflow is encoded as an explicit FSM with states such as `COLLECT_REQUIREMENTS`, `PLAN`, `SEARCH`, `DRAFT`, `REVIEW`, `FINALIZE`.
   - For each state, only a subset of tools is permitted.
   - Transitions between states must satisfy guard predicates (e.g., cannot finalize before drafting).
   - The orchestrator consults the FSM to interpret model suggestions and apply guards, logging every transition.
   - Logs contain explicit state labels and guard outcomes for auditability.

In this repository, we simulate the model output using deterministic logic, but the agent orchestration and FSM scaffolding are written as they would be when using a real LLM.

## Limitations in This Sandbox Implementation

- No real LLM or network access is used; the focus is on orchestration and determinism, not language quality.
- Metrics are intentionally minimal because some of the richer metrics described in the long-form spec (like semantic ordering judged by a human or separate evaluator) would require natural language understanding.
- The experiment still highlights:
  - How an FSM can prevent certain invalid or out-of-order actions by construction.
  - How treatment logs include state and guard information absent from baseline logs.

## Extending This Experiment

If you want to adapt this code for a real model in a networked environment:

1. Replace the mock LLM in `tools.py` with a thin client for your chosen model API.
2. Preserve the public interfaces used by `agent_freeform.py` and `agent_fsm.py` for compatibility.
3. Enhance `evaluation.py` to compute the full suite of metrics from the original specification.
4. Be explicit about randomness controls (temperature, seeds) in your environment.

Always generate real metrics by running the code; do not fabricate or guess quantitative results.
