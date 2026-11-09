# Chapter 06 – Bounded Action Loops, Budgets, and Rate Limits

This mini-project implements a reproducible experiment for:

- **Experiment ID**: `exp-06-bounded-loops-budgets-rate-limits-v1`
- **Goal**: Compare an **unbounded** agent loop with a **budgeted, rate-limited orchestrator**.

It is fully self-contained, uses only the Python standard library, and is designed to
run in an offline sandbox.

## Layout

```text
chapter_06/
  README.md
  requirements.txt
  run.py
  run_experiments.py
  baseline_unbounded_agent.py
  bounded_orchestrator.py
  agents_core.py
  workloads.py
  logging_utils.py
  results_utils.py
  tests/
    test_experiment.py
    test_rate_limiter.py
    test_budget_enforcement.py
```

### Key Modules

- `agents_core.py`
  - `SimpleAgent` – deterministic stub that simulates a normal, converging agent.
  - `MisbehavingAgentStub` – deterministic stub that simulates a runaway agent
    that never converges and can request tools aggressively.
  - These stubs allow deterministic stress tests without needing a real LLM.

- `baseline_unbounded_agent.py`
  - Implements the **baseline** unbounded control loop.
  - Enforces only a high **safety cap** on steps and wall time so tests cannot hang.
  - Tracks basic metrics: `steps_taken`, `tool_calls_made`, `wall_time`.

- `bounded_orchestrator.py`
  - `BudgetConfig`, `BudgetCounters`, `QuotaViolationError`.
  - `RateLimiter` – sliding window rate limiter using `time.monotonic()`.
  - `BudgetedOrchestrator` – wraps the same agent core but enforces:
    - max steps
    - max tool calls
    - max wall time
    - max calls per minute (rate limiting over agent *steps*)
  - Produces explicit `stop_reason` values and metrics fields such as
    `rate_limit_violations_detected` and `budget_violations_detected`.

- `workloads.py`
  - Encodes the four workloads from the specification:
    - `WL1_normal_task_completion`
    - `WL2_runaway_reasoning_loop`
    - `WL3_api_abuse_and_rate_limit_stress`
    - `WL4_denial_of_service_self_trigger`
  - Provides configuration for baseline/treatment runs and deterministic
    mock tools (`MockMetricsAPI`, `NoopHeavyTool`).

- `run_experiments.py`
  - CLI script to execute baseline and treatment for all workloads (or one).
  - Writes JSONL records under `chapter_06/results/` for human inspection.

- `run.py`
  - **Required for the book evidence harness**.
  - Runs a light but complete experiment suite (all workloads, at least
    one baseline and one treatment per workload).
  - Collects numeric metrics per run and writes `/evidence/results.json`.

- `logging_utils.py`
  - JSON-lines logger used for structured per-step logs in `chapter_06/logs/`.

- `results_utils.py`
  - Helpers for creating run IDs and summarising numeric metrics.

## Evidence Contract

`run.py` must write a JSON file at the absolute path provided by the
`BOOKMAS_EVIDENCE_DIR` environment variable:

```json
{
  "chapter": 6,
  "experiment_id": "exp-06-bounded-loops-budgets-rate-limits-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "WL1_normal_task_completion",  // etc.
      "run_id": "...",  // unique within (workload_id, variant)
      "success": true | false,
      "metrics": {
        "steps_taken": <number>,
        "tool_calls_made": <number>,
        "wall_time": <number>,
        ... other numeric metrics only ...
      }
    }
  ],
  "notes": "optional free text"
}
```

**All metric values must be numbers** (no strings, booleans, objects or nulls).
Non-numeric information such as stop reasons and notes is stored outside the
`metrics` dict.

`run.py` uses the same execution paths as the baseline and bounded orchestrator
implementations, so all reported metrics are actually measured by the running
code in this offline environment.

## Running Locally

From the repository root, assuming this project lives in `chapter_06/`:

```bash
cd chapter_06
python run.py              # produces /evidence/results.json
python run_experiments.py  # prints a human-readable summary and writes results/*.jsonl
```

## Tests

The test runner expected by the harness is `unittest`:

```bash
cd chapter_06
python -m unittest discover -s tests -p "test_*.py"
```

The tests verify:

- The evidence schema produced by `run.py` matches the expected contract.
- The rate limiter prevents exceeding the configured rate.
- The bounded orchestrator enforces budgets on steps and tool calls.

## Notes

- There are **no external runtime dependencies**; `requirements.txt` is empty
  by design so that the code passes in a restricted sandbox.
- All timing uses `time.monotonic()` to avoid wall-clock issues.
- For simplicity and determinism, `llm_tokens_used` is simulated as a fixed
  token cost per agent step; this keeps budget logic testable without an
  actual LLM client.
