# Chapter 8 – Transactional Execution and Reversible Actions

This mini-project implements an experiment for:

- **Chapter**: 8
- **Experiment ID**: `exp-08-transactional-execution-reversible-actions-v1`
- **Title**: Transactional Execution and Reversible Actions

It compares a **baseline agent** that calls tools directly (with irreversible side effects) to a **transactional agent** that wraps tool invocations in a transactional layer with compensating (undo) actions and crash recovery using a persisted log.

The project is completely self-contained, uses only the Python standard library, and is runnable in an offline sandbox.

## Layout

- `run.py` – main entry point that executes a small sample of workloads and writes evidence to `/evidence/results.json` (or `$BOOKMAS_EVIDENCE_DIR/results.json`).
- `requirements.txt` – intentionally empty of third-party runtime dependencies.
- `chapter_08_transactional_execution/transactional_agent.py` – baseline and transactional agents and workflow definitions.
- `chapter_08_transactional_execution/tools.py` – baseline and transactional tools (file and in-memory order store, optional SQLite integration stub).
- `chapter_08_transactional_execution/transaction_manager.py` – transaction manager, action log entries, and simple persistent logging to a JSON-lines file.
- `chapter_08_transactional_execution/recovery.py` – recovery coordinator that replays compensating actions based on the transaction log.
- `chapter_08_transactional_execution/tests/` – unit tests implementing workloads 1–3 and failure-mode tests.
- `tests/test_experiment.py` – high-level tests asserting the evidence schema produced by `run.py`.

## Running the Experiment

From the project root:

```bash
python run.py
```

This will:

1. Execute a subset of the defined workloads for both baseline and treatment variants.
2. Measure simple numeric metrics (e.g., `partial_side_effects_count`, `log_entries_per_transaction`).
3. Write evidence JSON to `/evidence/results.json` (creating `/evidence` if necessary). You can override the directory with `BOOKMAS_EVIDENCE_DIR`.

Example:

```bash
BOOKMAS_EVIDENCE_DIR=/tmp/evidence python run.py
cat /tmp/evidence/results.json
```

## Running Tests

The test suite uses the standard library `unittest` framework and should be run as:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests cover:

- **Baseline vs transactional behavior**: ensuring that on failure, the baseline leaves partial side effects while the transactional agent rolls back.
- **Randomized failure points** (with fixed random seeds) to validate rollback correctness at different points in the workflow.
- **Crash recovery**: simulating a crash between forward actions and rollback, then using a persisted transaction log to recover.
- **Compensation failure modes**: ensuring compensating actions are idempotent and that failures are surfaced without corrupting state.
- **Evidence schema**: `tests/test_experiment.py` asserts that `run.py` writes evidence matching the specified schema.

## Notes on Design

- **No external dependencies**: Everything uses the Python standard library (e.g., `json`, `random`, `unittest`, `sqlite3`, `os`, and `pathlib`).
- **Filesystem isolation**: All tests write to per-test temporary directories and never touch global paths except the `/evidence` directory used by `run.py`.
- **Determinism**: Randomized tests seed the RNG with fixed values; no wall-clock timestamps are used in assertions.
- **Metrics**: Metrics in the evidence file are true numeric values derived from actual execution. The code never fabricates measurements.

## Evidence Schema (Runtime Contract)

`run.py` writes evidence to `${BOOKMAS_EVIDENCE_DIR:-/evidence}/results.json` as:

```json
{
  "chapter": 8,
  "experiment_id": "exp-08-transactional-execution-reversible-actions-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "workload-...",
      "run_id": "unique string",
      "success": true,
      "metrics": {
        "partial_side_effects_count": 0,
        "log_entries_per_transaction": 2
      }
    }
  ],
  "notes": "... optional ..."
}
```

- At least **one baseline** and **one treatment** run are recorded per workload.
- All metric values are **numbers**.
- Additional non-metric fields (e.g., notes) may be included but are never interpreted as metrics.

## Safety & Bounded Execution

- The workflows are small and use in-memory structures and small JSON files; they are safe to run within the constraints of a typical CI sandbox.
- No network, shell commands, or external processes are used.
