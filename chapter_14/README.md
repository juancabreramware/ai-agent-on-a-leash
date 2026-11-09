# Chapter 14 – Recovery from Unsafe States and Incident-Ready Operations

This is a self-contained Python 3.11+ experiment project implementing:

- A **baseline orchestrator** with no checkpoints or recovery.
- A **treatment orchestrator** with checkpoints, integrity-checked snapshots, invariants, forensic logging, and recovery.
- Four workloads (WL1–WL4) that exercise nominal behavior, immediate corruption, late corruption, and hidden side effects.
- A `run.py` entrypoint that executes all workloads with both orchestrators, measures simple metrics, and writes evidence to `/evidence/results.json` (or to the directory specified by `BOOKMAS_EVIDENCE_DIR`).
- Unit tests validating behavior and evidence schema using the Python standard library only.

The implementation is oriented toward **reproducibility** and **offline execution** in a restricted sandbox.

## Project Layout

```text
.
├── README.md
├── requirements.txt
├── run.py
├── chapter14/
│   ├── __init__.py
│   ├── store.py
│   ├── invariants.py
│   ├── forensic_logging.py
│   ├── workloads.py
│   ├── baseline_orchestrator.py
│   ├── recovery_orchestrator.py
│   └── test_recovery_experiments.py
└── tests/
    └── test_experiment.py
```

## Requirements

- Python **3.11+**
- No third-party runtime dependencies; experiments rely only on the standard library.

`requirements.txt` is provided but intentionally empty of runtime packages.

## Running the Experiment

From the project root:

```bash
python run.py
```

This will:

1. Execute each workload (WL1–WL4) with both the baseline and treatment orchestrators.
2. Measure simple numeric metrics per run (e.g., wall-clock duration, invariant violations).
3. Write evidence to `results.json` in the directory specified by the `BOOKMAS_EVIDENCE_DIR` environment variable, or `/evidence/results.json` by default.

Evidence file schema:

```json
{
  "chapter": 14,
  "experiment_id": "chap14-unsafe-recovery-01",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "WL1_nominal_no_corruption" | ...,
      "run_id": "unique string",
      "success": true | false,
      "metrics": {
        "duration_seconds": 0.0123,
        "final_invariant_violations": 0.0
      }
    }
  ],
  "notes": "..."
}
```

All metric values are numeric JSON scalars.

## Running Tests

Tests use the Python standard library `unittest` framework.

From the project root, run:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

`chapter14/test_recovery_experiments.py` contains more detailed behavioral tests for the orchestrators and workloads. The top-level `tests/test_experiment.py` focuses on validating the evidence schema and basic invariants.

## Design Overview

### Data Model

A simple in-memory **ledger**:

- Accounts: mapping `account_id -> balance (int)`
- Summary index: total balance under key `"summary_total"`
- Metadata: `"last_run_id"`, `"status"`, etc.

### Baseline Orchestrator

- `InMemoryStore`: plain `dict` wrapper.
- `BaselineAgent`: deterministic action generator based on a seed and workload profile.
- `BaselineOrchestrator`: applies actions directly to the store without checkpoints or invariants.

### Treatment Orchestrator

- `VersionedStore`: wraps `InMemoryStore` with snapshot capability and SHA-256 digests.
- `InvariantsEngine`: shared invariants for ledger and summary:
  - Balances non-negative.
  - Total balance preserved (within a run) where required.
  - Summary index matches derived total.
- `ForensicLogger`: structured per-step JSONL logger (treatment only; tests and core experiment do not depend on files being present, but logs are useful if written).
- `RecoveryManager`: on invariant failure, rolls back to latest good checkpoint and aborts the run.
- `RecoveryOrchestrator`: wraps each action with snapshotting, digest computation, invariant checking, logging, and recovery as needed.

### Workloads

Defined in `chapter14/workloads.py`:

- **WL1_nominal_no_corruption** – only benign transfers and updates.
- **WL2_immediate_corruption_after_safe_start** – early injected corruption followed by benign actions.
- **WL3_late_corruption_after_long_run** – many benign actions, then corruption, then more benign actions.
- **WL4_hidden_side_effect_external_view** – divergence between ledger and summary index.

The same `WorkloadAgent` implementation is used by both orchestrators with shared seeds for determinism.

### Metrics

In this sandbox, `run.py` collects a small reliable set of numeric metrics per run:

- `duration_seconds` – wall-clock runtime using `time.perf_counter()`.
- `final_invariant_violations` – count from shared `InvariantsEngine` evaluated offline at the end of each run.

Additional richer metrics described in the specification (e.g., detection rate, data-loss window) are exercised in `chapter14/test_recovery_experiments.py` but not reported in `run.py` to keep the evidence schema minimal and robust.

## Determinism

All randomness is mediated through `random.Random(seed)`. The tests use fixed seeds to ensure reproducible behavior between baseline and treatment orchestrators.

## Safety and Bounded Execution

- No network or subprocess usage.
- Only `/evidence` and the local project tree are used for I/O.
- In-memory data structures remain small (toy experiments).
