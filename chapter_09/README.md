# Chapter 09 – Human Approval Gates for High-Risk Operations

This mini-project demonstrates **human approval gates** for high-risk operations
using a small, fully self-contained Python codebase and experiments.

It implements both:

- **Baseline**: an agent that calls sensitive tools directly with **no** approval.
- **Treatment**: an agent whose sensitive tool calls are routed through an
  **approval gateway** with pending actions, approval/denial/timeout states, and
  deterministic human simulator.

The project is intentionally simple, deterministic, and uses only the Python
standard library. Experiments are designed to be reproducible and to emit
structured evidence JSON for automatic validation.

## Layout

- `run.py` – Orchestrates baseline vs treatment workloads and writes
  evidence to `${BOOKMAS_EVIDENCE_DIR}/results.json`.
- `src/`
  - `approval_gateway.py` – ApprovalGateway and state machine.
  - `agent_baseline.py` – Simple agent that invokes tools directly.
  - `agent_with_approval.py` – Agent that routes sensitive actions via
    ApprovalGateway.
  - `pending_store.py` – In-memory PendingAction store and types.
  - `risk_scoring.py` – Deterministic risk scoring by tool name.
  - `human_simulator.py` – Deterministic human approver/denier/ignorer.
  - `tools.py` – Simple simulated high-risk and low-risk tools with a shared
    in-memory side-effect store.
  - `workloads.py` – Deterministic workload definitions and runners for
    baseline and treatment variants.
- `tests/`
  - `test_approval_gateway.py` – Unit tests for the gateway and state machine.
  - `test_experiment.py` – End-to-end tests for workloads and evidence
    `results.json` schema.

## Experiments

### Workloads

The project implements the four workloads described in the specification:

1. **WL1_auto_approve_high_risk** – High-risk operations auto-approved.
2. **WL2_auto_deny_high_risk** – High-risk operations auto-denied.
3. **WL3_timeout_no_response** – High-risk operations time out.
4. **WL4_mixed_risk_routing** – Mixed low/medium/high-risk routing.

Each workload is run once for baseline and once for treatment. For each
run we record at least one numeric metric (e.g., executed action count).

### Evidence Output Contract

`run.py` writes a single JSON file to `${BOOKMAS_EVIDENCE_DIR}/results.json`:

```json
{
  "chapter": 9,
  "experiment_id": "exp-ch09-human-approval-gates-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" or "treatment",
      "workload_id": "WL1_auto_approve_high_risk",  // etc.
      "run_id": "unique-run-id",
      "success": true,
      "metrics": {"some_metric": 1.0}
    }
  ],
  "notes": "optional text"
}
```

**Important constraints (enforced in tests):**

- At least one **baseline** and one **treatment** run per workload.
- All metric values must be JSON **numbers** (no strings, booleans,
  objects, arrays, or nulls inside `metrics`).
- Metrics must be **measured from actual execution** (e.g., counts derived
  from the tools' side-effect store, measured timings). Nothing is
  fabricated.

## Running Tests

From the `chapter_09_human_approval_gates` directory:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

All tests should pass using Python 3.11+ and no extra dependencies.

## Running the Experiment and Generating Evidence

Set the evidence directory and run `run.py`:

```bash
export BOOKMAS_EVIDENCE_DIR=/evidence   # or another writable directory
python run.py
```

This will:

1. Reset the global side-effect store.
2. Execute the four workloads for both baseline and treatment variants.
3. Compute simple numeric metrics (e.g., executed operation counts and
   latencies).
4. Write `results.json` to `${BOOKMAS_EVIDENCE_DIR}`.

You can open that file to inspect metrics per workload and variant.

## Determinism and Safety

- No network or filesystem access outside the project and `/evidence`.
- All random-like choices are deterministic (no `random` usage).
- Delays and latencies use `time.monotonic()` but do not sleep for long
  periods (timeouts are simulated with very small delays in tests).
- Experiments use in-memory stores and are fast to run.

## Extending

To integrate with real systems (ticketing, chat, incident management), you
could replace or extend `HumanApprover` in `human_simulator.py` with classes
that call external APIs and re-run experiments, preserving the same public
interfaces and evidence schema.
