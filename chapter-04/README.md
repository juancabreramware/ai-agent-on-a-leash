# Chapter 4 – Policy Enforcement Gateway Experiment

This is a self-contained, offline Python 3.11+ experiment project for:

- **Number:** 4
- **Title:** Policy Enforcement Gateways for Agent Actions
- **Experiment ID:** `exp-4-policy-gateway-v1`

It demonstrates how to interpose a **policy enforcement gateway** between a tool-using agent and its tools, and compares a baseline agent (no gateway) against a treatment agent (gateway-protected).

The code is intentionally minimal and uses **only the Python standard library** so it can run in restricted sandboxes.

## Layout

- `run.py` – Entry point for the experiment. Produces evidence at `/evidence/results.json`.
- `chap_04_policy_gateway/`
  - `__init__.py`
  - `tools.py` – Mock tool implementations (purchase orders, customer data access, deployments, exports).
  - `workloads.py` – Workload definitions WL1–WL4 and synthetic LLM action plans.
  - `baseline_agent.py` – Baseline tool-using agent without policy enforcement.
  - `audit.py` – Structured logging utilities and in-memory auditor.
  - `policies.py` – Declarative policy definitions for spending, data access, time windows, and export limits.
  - `decision_engine.py` – Deterministic policy decision engine.
  - `gateway_agent.py` – Treatment agent using a `PolicyInterceptor` gateway for tools.
  - `run_experiments.py` – Programmatic experiment runner used by `run.py`.
- `tests/`
  - `test_experiment.py` – Unit tests verifying the evidence schema and basic behavioral differences between baseline and gateway variants.
- `requirements.txt` – Empty of runtime deps (comments only), per sandbox requirements.

## Running the Experiment

From the project root:

```bash
python run.py
```

This will:

1. Detect a writable evidence directory via the `BOOKMAS_EVIDENCE_DIR` environment variable, or default to `/evidence`.
2. Execute all workloads for both variants (`baseline` and `treatment`).
3. Measure simple numeric metrics (e.g., counts and per-run elapsed time in milliseconds).
4. Write `/evidence/results.json` with the following schema:

```jsonc
{
  "chapter": 4,
  "experiment_id": "exp-4-policy-gateway-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "wl1_case1_small_purchase",  // etc.
      "run_id": "baseline-wl1_case1_small_purchase-1", // stable unique
      "success": true,
      "metrics": {
        "actions_executed": 1,
        "run_elapsed_ms": 0.42
      }
    }
  ],
  "notes": "Free-text notes about the experiment (non-metric metadata)."
}
```

All values in the `metrics` objects are **actual numeric measurements** obtained at runtime. No values are fabricated.

At least one **baseline** and one **treatment** run is recorded per workload case.

## Running Tests

Tests use only the standard library `unittest` framework.

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests assert that:

- `run.py` creates `/evidence/results.json` with the required top-level keys.
- Each `run` entry contains the required fields and a `metrics` mapping of finite numeric values.
- Both `baseline` and `treatment` variants appear for each workload.
- Basic behavioral differences exist (e.g., policy-violating actions are blocked by the gateway where the baseline executes them).

## Conceptual Overview

The project illustrates these chapter sections:

- **4.1 Problem:** Baseline agent embeds policy _only_ in prompts / docstrings (simulated via workload labels), with no enforcement in code.
- **4.2 Failure Modes:** Baseline will execute policy-violating tool calls; there is no central policy store, no auditing, and no deterministic guard.
- **4.3 Pattern Overview:** The treatment wraps the shared tool registry in a `PolicyInterceptor` that enforces policies for every call.
- **4.4 Architecture:**
  - `PolicyInterceptor` – Intercepts tool calls.
  - `PolicyStore` (in `policies.py`) – Static in-memory policy config.
  - `DecisionEngine` – Applies policies deterministically to an `ActionContext`.
  - `Auditor` – Records structured audit events.
- **4.5 Policies:** Implemented as Python predicates with IDs and metadata; they could be replaced with a DSL without changing the interceptor interface.
- **4.6 Python Implementation:** `gateway_agent.py` and `decision_engine.py` show the concrete gateway implementation.
- **4.7 Experiments:** `run_experiments.py` executes WL1–WL4 over baseline and treatment, gathering measurements and writing evidence.
- **4.8 Operational Concerns:**
  - Deterministic decisions (no randomness, no LLM in the decision path).
  - Potential caching extension points noted in comments.
  - Audit logs cover every attempted action in the treatment variant.

## Extending the Experiment

You can extend this experiment by:

- Adding more workloads or tools to `workloads.py` and `tools.py`.
- Adding new policy rules (e.g., per-department limits) in `policies.py`.
- Enhancing metrics collection (e.g., histogram of decision latencies) in `run_experiments.py` and `run.py`.
- Writing small analysis scripts or notebooks that consume `results.json` and the in-memory audit logs (if persisted) to compute the richer metrics described in the original specification.

This project is designed to be minimal yet illustrative; it focuses on the **mechanics** of a policy gateway and on producing reproducible measurements in a controlled environment.
