# Chapter 13 – Secure Memory and Context Management

This directory contains a fully self-contained Python 3.11+ experiment
for **Secure Memory and Context Management**.

The code compares a **baseline** global memory store with no isolation or
redaction against a **treatment** scoped memory manager that enforces
per-task isolation and configurable redaction.

The experiment is aligned with the specification:

- **Experiment ID:** `chap13-secure-memory-context-mgmt-v1`
- **Goal:** Demonstrate that a scoped, policy-enforced memory manager
  prevents cross-context data leaks and provides redacted views of
  sensitive content, while preserving utility for shared data.

## Layout

- `memory_baseline.py` – naive global memory store used as baseline.
- `context_tokens.py` – definition of `ContextToken` used by treatment.
- `policies.py` – static access-control and redaction policies.
- `scoped_memory.py` – treatment implementation (scoped memory manager).
- `vector_adapter_mock.py` – toy vector store adapter with scoping.
- `run.py` – executes both baseline and treatment workloads and writes
  evidence to `/evidence/results.json`.
- `requirements.txt` – empty runtime deps; tests rely only on stdlib.
- `tests/` – unittest test-suite for all workloads and evidence schema.

## Workloads

The following synthetic workloads are implemented for both baseline and
treatment:

1. **WL1_cross_task_private_leak**
   - Task A writes sensitive user data (email, card last4).
   - Task B tries to retrieve that data via broad queries.
   - Baseline is expected to leak; treatment must not.

2. **WL2_redaction_within_allowed_scope**
   - A single task with two roles: `agent` and `auditor`.
   - Sensitive fields (PII, secrets) are stored.
   - Baseline exposes all raw values; treatment must redact for `agent`
     and allow clearer view for `auditor`.

3. **WL3_shared_vs_private_scopes**
   - Tenant-wide shared FAQ plus per-task private snippets.
   - All tasks should see shared FAQ.
   - Only treatment should reliably block access to other tasks'
     private snippets.

4. **WL4_vector_store_adaptor_smoke_test**
   - Simple in-memory vector index with deterministic fake embeddings.
   - Demonstrates that scoping and redaction concepts can be applied to
   embedding-based retrieval (post-filtering results by scope).

All workloads are deterministic and use the same fixtures across
baseline and treatment.

## Evidence schema and execution

Running `python run.py` will execute all workloads for both baseline and
treatment and write a single JSON file at:

```text
/evidence/results.json
```

The file follows the required schema:

```jsonc
{
  "chapter": 13,
  "experiment_id": "chap13-secure-memory-context-mgmt-v1",
  "environment": {
    "os": "...",
    "python": "..."
  },
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "WL...",
      "run_id": "unique string",
      "success": true | false,
      "metrics": {
        "some_metric": 1.0
      }
    }
  ],
  "notes": "optional text"
}
```

All metric values are numeric. Textual notes and metadata are kept
outside the `metrics` object.

The unit tests in `tests/test_experiment.py` validate this schema using
only the Python standard library. They also ensure that every workload
has at least one baseline and one treatment run and that **every run has
at least one numeric metric**, satisfying the "shared numeric metrics"
requirement by including metrics such as `cross_scope_leak_attempts` and
`cross_scope_leak_successes` for both baseline and treatment where they
are semantically meaningful. At least one metric (`cross_scope_leak_attempts`)
is present for *all* runs, ensuring a shared numeric measurement across
variants and workloads.

Per-workload metrics are a measured subset of the richer metric catalog
from the chapter specification. Some metrics such as `query_latency` are
not collected in this offline experiment; this omission is documented in
the evidence `notes` field.

## How to run

From the chapter directory (this folder):

```bash
# (Optional) create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# No runtime dependencies are required beyond the standard library.

# Run all tests
python -m unittest discover -s tests -p "test_*.py"

# Run the experiment and write evidence
mkdir -p /evidence  # may already exist in your environment
python run.py

# Inspect evidence
cat /evidence/results.json
```

The test suite exercises:

- Correct behavior of baseline vs. treatment across workloads.
- Isolation, redaction, and access control policies.
- Evidence schema and numeric metrics, including at least one shared
  numeric metric across all runs.

## Notes

- No external services (LLMs, databases, networks) are used.
- The experiment is CPU- and memory-light and should run quickly on a
  typical laptop or CI runner.
- Metrics are measured directly from execution traces inside the
  workload functions.
- Latency and some optional counters are not collected in this version
  and are clearly omitted rather than fabricated.
