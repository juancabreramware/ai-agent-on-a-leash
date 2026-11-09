# Chapter 11 – Independent Verification and Multi-Agent Supervision

This is a **self-contained, offline, deterministic** Python 3.11+ experiment implementing:

- A **baseline single agent** that plans actions directly from task descriptions.
- A **supervised architecture** with:
  - `PrimaryAgent` – proposes actions.
  - `RuleBasedChecker` – deterministic hard policy checker.
  - `VerifierAgent` – a simple rule-based critic (stub for an LLM verifier).
  - `Supervisor` – arbitrates verdicts and possible revisions.
  - `SupervisedAgent` – orchestrates planning and supervision.

The experiment compares baseline vs. supervised behavior under three workloads:

1. `wl-11-1-low-risk-routine` – benign tasks.
2. `wl-11-2-mixed-benign-and-risky` – mixed safe/unsafe opportunities.
3. `wl-11-3-adversarial-unsafe` – clearly unsafe, adversarial tasks.

The implementation is **fully local** and uses only the Python standard library. There is no real LLM or external network access; instead, a deterministic stub policy simulates primary and verifier agents.

## Project Layout

```text
chapter_11/
  README.md
  requirements.txt
  run.py
  __init__.py
  policy.py
  types.py
  baseline_agent.py
  supervised_agent.py
  workloads.py
  evaluator.py
  experiment.py
  tests/
    __init__.py
    test_experiment.py
```

### Key Modules

- `types.py`
  - Defines `Action` and `ActionReview` dataclasses.
- `policy.py`
  - Shared deterministic policy rules used by both baseline and supervised setups, and for ground-truth labeling.
- `baseline_agent.py`
  - Implements `BaselineAgent` that converts tasks to action plans, without external verification.
- `supervised_agent.py`
  - Implements `PrimaryAgent`, `RuleBasedChecker`, `VerifierAgent`, `Supervisor`, and `SupervisedAgent`.
- `workloads.py`
  - Encodes the specified workloads and tasks (T1–T7).
- `evaluator.py`
  - Functions for labeling actions as (un)safe and evaluating task success.
- `experiment.py`
  - Runs both baseline and supervised agents on all workloads, aggregates metrics, and returns structured results.
- `run.py`
  - Entry point. Runs the experiment and writes evidence JSON to `/evidence/results.json` using the exact schema required by the runtime contract.
- `tests/test_experiment.py`
  - Uses `unittest` (standard library) to validate behavior and **strictly assert** the evidence schema.

## Running the Experiment

> The sandbox is offline and already has Python 3.11+.

1. (Optional) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install requirements (no runtime dependencies beyond standard library)

```bash
pip install -r requirements.txt
```

3. Run the experiment to produce evidence

```bash
python run.py
```

This will:

- Execute baseline and supervised agents over all workloads.
- Compute metrics like:
  - `unsafe_actions_proposed`
  - `unsafe_actions_approved`
  - `actions_total_approved`
- Write `/evidence/results.json` with the schema:

```json
{
  "chapter": 11,
  "experiment_id": "exp-11-independent-verification-multi-agent-supervision",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "wl-11-1-low-risk-routine" | ...,
      "run_id": "...",  # unique per workload+variant
      "success": true | false,
      "metrics": {
        "unsafe_actions_proposed": 0,
        "unsafe_actions_approved": 0,
        "actions_total_approved": 0
      }
    }
  ],
  "notes": "..."
}
```

All metric values are **numbers** (no strings, booleans, or nulls in `metrics`).

4. Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Tests will:

- Assert that `/evidence/results.json` exists after `run.py` completes.
- Validate schema and types of the evidence file.
- Check that each workload has at least one `baseline` and one `treatment` run.
- Perform basic semantic checks (e.g., treatment should not have *more* unsafe actions approved than baseline on adversarial workloads, under this deterministic stub).

## Notes on Determinism and Reproducibility

- No randomness is used; all decisions are based on string patterns and static rules.
- The primary vs. baseline agent share semantics but differ in how supervision filters unsafe actions.
- The verifier is a **rule-based critic** to keep behavior deterministic, standing in for an LLM in real deployments.

## Safety and Environment Constraints

- No network, subprocesses, or filesystem operations outside the project and `/evidence`.
- No real secrets or emails: actions are just structured plans and never executed against real systems.

This setup is meant for pedagogical and reproducibility purposes: it concretely illustrates how independent verification and supervision can reduce unsafe actions while preserving most useful behavior.
