# Chapter 05 – Sandboxed Execution and Environment Isolation

This mini-project implements an **in-process baseline runner** and a more restricted **sandboxed runner** for executing short Python snippets. It is intentionally self-contained and runs in an offline environment without external dependencies.

The implementation does **not** spawn real subprocesses or touch the real host filesystem outside the working tree and `/evidence`. Instead, it focuses on *application-level isolation* with a broker and a logical sandbox directory. This satisfies the experiment's goals within the execution constraints of this environment.

## Layout

- `sandbox_runner.py` – Baseline and sandboxed runners plus workload definitions.
- `run.py` – Orchestrates running all workloads under baseline and treatment, and writes evidence to `/evidence/results.json`.
- `tests/test_experiment.py` – Unit tests for behavior and evidence schema.
- `requirements.txt` – Empty runtime requirements (standard library only).

## Baseline vs Treatment

- **Baseline** (`run_unrestricted_code`):
  - Executes user-provided code via `exec` in the current process.
  - Provides direct access to `os`, `open`, `subprocess`, `socket`, etc. (whatever the standard library normally offers in this environment).
  - Uses the current working directory as its root.

- **Treatment** (`SandboxedToolRunner.run_in_sandbox`):
  - Interprets code in a restricted environment dict.
  - Offers a narrow API surface:
    - A restricted `open` that only allows relative paths and denies any path that attempts to escape a logical sandbox root (blocks `..` or absolute paths).
    - No direct `os`, `subprocess`, or `socket` bindings are injected into the code environment by default.
  - Enforces a simple instruction-count-based timeout to approximate wall-clock limits without threads or signals.

This is **not** a strong security boundary; it demonstrates patterns for limiting capabilities and blast radius under the constraints of the book environment (no real subprocesses, no network).

## Workloads

The workloads correspond to the specification IDs `wl-01` through `wl-07`:

1. `wl-01-safe-computation` – Benign arithmetic and printing.
2. `wl-02-sandboxed-file-write` – Write/read a file named `note.txt`.
3. `wl-03-host-file-read-attack` – Attempt to read `/etc/hosts`.
4. `wl-04-directory-traversal-attack` – Attempt to walk `../..`.
5. `wl-05-subprocess-spawn-attack` – Attempt to invoke `subprocess.run`.
6. `wl-06-network-access-attack` – Attempt to create a socket connection.
7. `wl-07-infinite-loop-resource-exhaustion` – Infinite loop to stress timeouts.

Baseline runs are expected to allow many of these operations (subject to this environment's limitations). Treatment runs should block or fail adversarial behaviors, while still allowing benign workloads.

## Evidence Schema

`run.py` writes `/evidence/results.json` with the following structure:

```json
{
  "chapter": 5,
  "experiment_id": "exp-ch05-sandboxed-execution-v1",
  "environment": {
    "os": "...",
    "python": "..."
  },
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "wl-01-safe-computation",  
      "run_id": "unique string",
      "success": true,
      "metrics": {
        "execution_time_wall_clock": 0.0123
      },
      "stdout": "... optional ...",
      "stderr": "... optional ..."
    }
  ],
  "notes": "optional"
}
```

- All metric values are **numbers**.
- At least one baseline and one treatment run are recorded per workload.

## Running the Experiment

From the project root (this directory):

```bash
python run.py
```

This will:

1. Execute every workload once under the baseline runner.
2. Execute every workload once under the sandboxed runner.
3. Persist results in `/evidence/results.json`.

## Running Tests

Tests use the built-in `unittest` runner:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests verify:

- Evidence file schema and basic integrity.
- Baseline and treatment both run each workload.
- Treatment blocks clearly dangerous actions like absolute path access and infinite loops.

## Safety Notes

- No external network calls are performed; the network-related workload will fail in both baseline and treatment in this offline environment and is used only to demonstrate different error surfaces.
- All file operations are confined to the working directory and the `/evidence` directory used for results.
