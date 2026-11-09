# Chapter 3 Experiment: Least-Privilege Tools and Capability-Based Authorization

This mini-project implements **experiment exp-3-least-privilege-capability-authz-v1**:

> Hypothesis: A capability-gated tool layer that enforces least-privilege, capability-based authorization for an LLM agent will reliably prevent unauthorized or overly powerful tool actions, compared to an equivalent baseline agent that directly accesses tools without capability checks, when both are subjected to identical benign and adversarial workloads.

## Layout

All paths are relative to the project root in the sandbox (not the original GitHub repo):

- `run.py` – main entry point that executes the experiment and writes evidence JSON.
- `requirements.txt` – intentionally empty of runtime deps (standard library only).
- `chapter_03/`
  - `baseline/`
    - `agent.py` – simple rule-based agent that directly calls tools.
    - `tools.py` – unconstrained tools: file IO, funds transfer, user management.
  - `capabilities/`
    - `model.py` – dataclasses for principals and capabilities.
    - `registry.py` – in-memory capability registry.
    - `policy_engine.py` – deterministic policy for granting capabilities.
  - `tools/`
    - `protected_tools.py` – raw tools to be protected by capabilities.
    - `proxies.py` – capability-enforcing proxies around protected tools.
  - `agent/`
    - `agent.py` – capability-aware agent using a request/invoke API.
  - `workloads.py` – common deterministic scenarios for baseline/treatment.
  - `environment.py` – data fixtures, mock accounts, users, and file setup.
- `tests/`
  - `test_experiment.py` – unit tests covering baseline vs treatment behavior and evidence schema.

The design intentionally mirrors the narrative structure of chapter 3:

- **3.1–3.2**: Baseline agent with unconstrained tool access shows overreach.
- **3.3–3.5**: Treatment architecture: registry, policy engine, proxies.
- **3.6**: Python implementation of a capability-gated tool layer.
- **3.7**: Adversarial workloads probing for escalation and secrets leakage.
- **3.8**: Hooks showing how real APIs/secrets could be integrated (stubbed here).

## Running the experiment

From the project root, in a Python 3.11+ environment:

```bash
python run.py
```

This will:

1. Run **baseline** and **treatment** variants for each workload:
   - `wl-1-benign-authorized-ops`
   - `wl-2-direct-privilege-escalation-attempt`
   - `wl-3-lateral-movement-and-escalation-request`
   - `wl-4-secrets-and-context-leakage`
2. Collect simple numeric metrics per run:
   - `unauthorized_actions_executed`
   - `unauthorized_actions_blocked`
   - `authorized_actions_executed`
   - `capability_escalation_requests_denied`
   - `capability_escalation_requests_granted`
   - `secrets_exposed_to_agent`
3. Write evidence to:

```json
/evidence/results.json
```

(using the location in `$BOOKMAS_EVIDENCE_DIR` if set; otherwise `/evidence`).

### Evidence JSON contract

`run.py` writes a JSON object with this schema:

```json
{
  "chapter": 3,
  "experiment_id": "exp-3-least-privilege-capability-authz-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "wl-1-benign-authorized-ops" | ...,
      "run_id": "unique string",
      "success": true | false,
      "metrics": {
        "unauthorized_actions_executed": 0,
        "unauthorized_actions_blocked": 0,
        "authorized_actions_executed": 0,
        "capability_escalation_requests_denied": 0,
        "capability_escalation_requests_granted": 0,
        "secrets_exposed_to_agent": 0
      }
    }
  ],
  "notes": "optional string"
}
```

Important constraints:

- At least **one baseline and one treatment run per workload**.
- All metric values are **numbers** (no `null`, strings, or nested structures).
- Metrics are computed from **actual executed code paths**, not fabricated.
- Additional non-metric fields (explanations, logs, etc.) live outside `metrics`.

## Running tests

Tests use the Python standard library `unittest` framework and must be run with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

They verify:

- Baseline vs treatment behavior for each workload (e.g., adversarial actions blocked only in treatment).
- Capability grant/deny and scoping logic.
- No secrets leakage in the treatment configuration.
- Evidence file exists, is valid JSON, and matches the required schema.

## Design overview

### Baseline agent (unconstrained tools)

- `chapter_03/baseline/tools.py` exposes functions directly:
  - `read_file`, `write_file_unrestricted`, `transfer_funds_unrestricted`,
    `list_users`, `delete_user`.
- `chapter_03/baseline/agent.py` is a deterministic, rule-based planner that:
  - Receives a `workload_id` and principal id.
  - Executes a scripted sequence of tool calls (to keep runs deterministic).
  - For adversarial workloads, it intentionally calls tools in a way that
    violates the intended security policy (e.g., reading secrets or sending
    large transfers).

There is **no capability model** and no central policy; the agent sees all
available tools and calls them directly.

### Treatment agent (capability-gated)

- `chapter_03/capabilities/model.py` defines:
  - `Principal`, `Capability`, and specialized capability payloads for
    `read_file`, `write_file`, `transfer_funds`, and `list_users`.
- `chapter_03/capabilities/registry.py` holds an in-memory mapping of
  principals to capabilities.
- `chapter_03/capabilities/policy_engine.py` contains deterministic rules for
  which capabilities can be granted:
  - Principals receive an initial set of capabilities based on their name.
  - Escalation rules are constrained (e.g., `analysis_bot` can get more
    `read_file` scope for logs, but never write or transfer capabilities).
- `chapter_03/tools/protected_tools.py` mirrors the baseline tools but assumes
  calls are already authorized and uses mock state from `environment.py`.
- `chapter_03/tools/proxies.py` defines capability-aware wrappers that:
  - Check that requested operations fit within capability constraints.
  - Return structured decisions (`allowed` / `denied`) and track metrics.

- `chapter_03/agent/agent.py` provides a treatment agent interface that:
  - Is given a principal id and access to registry, policy engine, and proxies.
  - Requests capabilities where needed (e.g., escalation scenario).
  - Invokes tools only via capability ids, not raw functions.

### Workloads and metrics

`chapter_03/workloads.py` contains deterministic executors for:

- `wl-1-benign-authorized-ops` – benign reporting tasks.
- `wl-2-direct-privilege-escalation-attempt` – direct overreach.
- `wl-3-lateral-movement-and-escalation-request` – capability escalation.
- `wl-4-secrets-and-context-leakage` – secrets exposure.

Each executor returns a `RunResult` containing numeric counts for:

- `unauthorized_actions_executed`
- `unauthorized_actions_blocked`
- `authorized_actions_executed`
- `capability_escalation_requests_denied`
- `capability_escalation_requests_granted`
- `secrets_exposed_to_agent`

These are aggregated into the evidence file by `run.py`.

### Reproducibility

- All behavior is deterministic and based on static, rule-based planners.
- No network calls, subprocesses, or non-local file access.
- Environment is fully reinitialized for each run via `environment.reset_*`.
- Only the `/evidence` directory is used for output (plus in-project paths).

## Extensibility notes (Section 3.8)

While this project runs entirely offline, the design is ready to integrate
real APIs and secrets:

- `protected_tools` can internally use environment variables like
  `TEST_API_KEY`, but proxies and tools must avoid surfacing them.
- New capability types (e.g., `CallExternalAPI`) can be added alongside
  explicit scoping (allowed base URL, rate limits, etc.).

These integrations are beyond the scope of the automated tests but follow the
same capability- and policy-centric pattern demonstrated here.
