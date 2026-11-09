# Chapter 12 – Continuous Monitoring, Circuit Breakers, and Emergency Shutdown

This mini-project implements an experiment for:

- **Chapter**: 12
- **Title**: Continuous Monitoring, Circuit Breakers, and Emergency Shutdown
- **Experiment ID**: `exp-12-continuous-monitoring-circuit-breaker-shutdown`

It compares a **baseline agent** with no monitoring or shutdown logic against a
**monitored agent** wrapped with metrics, a circuit breaker, and an emergency
shutdown manager. The monitored agent should stop executing tasks under
anomalous conditions, while the baseline continues.

The implementation is self-contained and uses only the Python standard library.

## Structure

- `run.py` – Orchestrates experiments and writes evidence JSON to `/evidence/results.json`.
- `chapter_12_circuit_breakers/`
  - `agent.py` – Baseline `SimpleAgent`, `MonitoredAgent`, and `ToolRunner`.
  - `monitoring.py` – `MetricsRecorder`, `Monitor`, `CircuitBreaker`, `EmergencyShutdownManager`.
  - `workloads.py` – Deterministic workload generators for WL1–WL4.
  - `run_experiments.py` – CLI for running baseline/treatment per workload with detailed logs and results.
- `tests/`
  - `test_experiment.py` – Unit tests for core logic and evidence schema.

## Running the experiment

1. Ensure Python 3.11+ is available:

   ```bash
   python --version
   ```

2. (Optional but recommended) Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```

3. Install test dependency (pytest is *not* required; we use unittest):

   ```bash
   pip install -U pip
   ```

4. Run the evidence-producing experiment script:

   ```bash
   python run.py
   ```

   This will:

   - Execute **baseline** and **treatment** for each workload WL1–WL4.
   - Collect metrics such as number of tasks executed and breaker transitions.
   - Write evidence to `/evidence/results.json` following the required schema:

     ```json
     {
       "chapter": 12,
       "experiment_id": "exp-12-continuous-monitoring-circuit-breaker-shutdown",
       "environment": {"os": "...", "python": "..."},
       "runs": [
         {
           "variant": "baseline" | "treatment",
           "workload_id": "WL1_nominal_low_error",
           "run_id": "...",
           "success": true,
           "metrics": {"tasks_executed": 50, ...}
         }
       ],
       "notes": "..."
     }
     ```

   The path `/evidence/results.json` may be overridden by setting the
   `BOOKMAS_EVIDENCE_DIR` environment variable to a directory path.

5. Optionally, run more detailed, per-workload experiments and inspect logs:

   ```bash
   cd chapter_12_circuit_breakers
   python run_experiments.py --all
   ```

   or, for example:

   ```bash
   python run_experiments.py --mode treatment --workload WL2_error_spike
   ```

   This writes per-run JSON files under `results/` and prints brief summaries.

## Running tests

Tests use the standard library `unittest` framework, as required.

From the repository root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests check:

- Circuit breaker state transitions under synthetic metrics.
- Rolling window metrics in the monitor.
- Baseline vs. treatment behavior for small samples of WL1–WL4.
- Correct structure of `/evidence/results.json` (schema, presence of baseline
  and treatment runs, numeric metrics).

## Notes on determinism and safety

- All workloads use a fixed random seed to ensure reproducible task sequences
  and latencies.
- Latency is simulated via `time.sleep` with small, bounded durations.
- No network, subprocess, or external filesystem access is used (besides the
  required `/evidence` directory for results).

## Extending the experiment

You can adjust circuit breaker thresholds in `monitoring.py` or by passing
arguments through `run_experiments.py` (for interactive exploration). When
modifying thresholds, make sure to update or extend tests accordingly so that
WL1 remains nominal (no spurious breaker openings) and WL2–WL4 still trigger
as expected.
