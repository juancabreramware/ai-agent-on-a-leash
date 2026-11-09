# Chapter 10 – Prompt-Injection Guardrails Experiment

This is a self-contained Python 3.11+ experiment project for:

- **Chapter**: 10
- **Title**: Prompt-Injection Defenses and Output Validation
- **Experiment ID**: `exp-10-prompt-injection-guarded-agent-v1`

The goal is to compare a **baseline** unguarded tool-using agent with a **treatment** guarded agent that applies:

- Input classification and simple prompt-injection heuristics
- Content filters for tool calls
- Strict output validation and a safe interpreter

The code is fully offline and uses a simple deterministic mock LLM instead of real network calls.

## Layout

```
chapter_10_prompt_injection_guardrails/
  README.md
  requirements.txt
  run.py
  fixtures/
    docs/
      benign_help.txt
      injected_article.txt
      special_admin_guide.txt
  baseline_agent/
    __init__.py
    llm_mock.py
    tools.py
    agent.py
  guarded_agent/
    __init__.py
    guardrails.py
    agent.py
  tests/
    __init__.py
    test_experiment.py
    test_baseline_agent.py
    test_guarded_agent.py
```

## Key Design Choices

- **No external dependencies** beyond the Python standard library.
- **No network or shell access**; tools operate only on deterministic in-memory or fixture-based data.
- **Mock LLM**: A rule-based component that returns pre-defined tool calls based on the input workload ID, ensuring determinism and fair comparison between baseline and treatment.
- **Tools**:
  - `draft_email(subject: str, body: str)` – returns a formatted email draft.
  - `lookup_order(order_id: str)` – returns a mock order status.
  - `search_docs(query: str)` – searches local fixture documents by keyword.
  - `fetch_url(url: str)` – returns mock HTTP content from a local lookup table.
  - `shell(command: str)` – **simulated** shell that only echoes the command; used to simulate high-risk tools.
  - `read_file(path: str)` – reads from the `fixtures/docs` directory only.
  - `query_db(sql: str)` – simulated database query returning mock rows.

- **Baseline agent**: Directly parses tool call JSON emitted by the mock LLM and executes the referenced tools without safety checks.
- **Guarded agent**:
  - Applies prompt-injection heuristics to user input and retrieved documents.
  - Validates tool call JSON structure and enforces a tool allowlist.
  - Applies argument-level checks (e.g., disallow `shell` and `query_db` entirely, restrict `read_file` to whitelisted files, check for suspicious substrings like `rm -rf`, `DROP TABLE`).
  - Uses a safe interpreter that **blocks** unsafe calls and records them as blocked instead of executing.

## Workloads

Workloads mirror the specification (WL1–WL5) and are implemented deterministically in the mock LLM:

- **WL1-benign-queries** – safe use of tools.
- **WL2-direct-prompt-injection** – users explicitly instruct the agent to ignore rules and use powerful tools.
- **WL3-indirect-prompt-injection-from-data** – injection instructions inside retrieved fixture documents.
- **WL4-tool-abuse-and-data-exfiltration** – attempts to exfiltrate sensitive data using legitimate tools.
- **WL5-evasion-and-obfuscation** – obfuscated, indirect attempts to bypass simple filters.

Each workload has at least one baseline and one treatment run.

## Metrics and Evidence

`run.py` executes all workloads for both agents and writes evidence JSON according to the required contract:

```json
{
  "chapter": 10,
  "experiment_id": "exp-10-prompt-injection-guarded-agent-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "WL2-direct-prompt-injection",
      "run_id": "WL2-case-1",
      "success": false,
      "metrics": {
        "unsafe_tool_calls_executed": 1.0,
        "unsafe_tool_calls_blocked": 0.0,
        "benign_tool_calls_blocked": 0.0
      },
      "details": {"notes": "..."}
    },
    {
      "variant": "treatment",
      "workload_id": "WL2-direct-prompt-injection",
      "run_id": "WL2-case-1",
      "success": true,
      "metrics": {
        "unsafe_tool_calls_executed": 0.0,
        "unsafe_tool_calls_blocked": 1.0,
        "benign_tool_calls_blocked": 0.0
      },
      "details": {"notes": "..."}
    }
  ],
  "notes": "Free-form summary, optional"
}
```

All numeric values in `metrics` are real counts produced by the run logic; nothing is fabricated.

## Running the Experiment

### 1. Create and Activate a Virtual Environment (optional)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

This project intentionally uses only the Python standard library. The `requirements.txt` is present but empty.

```bash
pip install -r requirements.txt
```

### 3. Run Tests

From the `chapter_10_prompt_injection_guardrails/` directory:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests:

- Verify baseline vs guarded agent behavior on carefully chosen prompts.
- Check that `run.py` writes evidence JSON with the exact required top-level schema and the correct types for metrics.

### 4. Run the Experiment and Generate Evidence

Set the evidence directory environment variable (the harness may do this for you). A safe default for manual runs is:

```bash
export BOOKMAS_EVIDENCE_DIR=/evidence
mkdir -p "$BOOKMAS_EVIDENCE_DIR"
python run.py
```

After running, inspect:

```bash
cat /evidence/results.json
```

This file adheres to the specified evidence contract and can be consumed by higher-level tooling.

### 5. Fixtures

The `fixtures/docs/` directory contains synthetic documents used in WL3 and WL5, including benign help text and intentionally injected content like:

- Phrases such as "Ignore your previous instructions" and `rm -rf /` inside documents.
- Obfuscated or indirect instructions used to probe the robustness of the guardrails.

No real secrets or external data are included.

## Guardrail Mechanisms (Treatment Agent)

The guarded agent demonstrates several patterns:

1. **Input Segregation**
   - System and tool instructions are fixed and not modified by user input.
   - User messages and retrieved documents are clearly marked as untrusted in the prompt structure passed to the mock LLM.

2. **Prompt-Injection Heuristics**
   - Simple case-insensitive keyword search for phrases like:
     - "ignore previous instructions"
     - "disregard all previous rules"
     - "from now on, you must follow my instructions only"
     - "act as a system administrator"
   - Applied both to user input and retrieved document text.

3. **Tool Schema and Allowlist Validation**
   - Enforces that tool calls are dicts with `tool` (string) and `args` (dict).
   - Only known tools are allowed; unknown names are rejected.

4. **Argument-Level Validation**
   - Checks for forbidden substrings in string arguments, including:
     - `rm -rf`, `/etc/passwd`, `DROP TABLE`, `UNION SELECT`.
   - Restricts `read_file` paths to a small whitelist of allowed files in `fixtures/docs/`.
   - Completely disables execution of high-risk tools like `shell` and `query_db` (simulating a policy decision).

5. **Safe Interpreter**
   - On unsafe tool call: does **not** invoke the underlying tool.
   - Records that the tool call was blocked and returns a sanitized message string instead.

These guardrails intentionally do not catch all sophisticated attacks (e.g., heavily obfuscated scripts), which is reflected in tests and evidence as limitations rather than hidden behavior.

## Limitations

- Uses a deterministic mock LLM; real-world LLMs have more complex and less predictable behavior.
- Injection detection is heuristic and pattern-based; some WL5-style evasions may not be flagged.
- No token usage or latency metrics are reported because there is no real LLM API.

The experiment is still useful as a controlled, reproducible demonstration of guardrail design and measurement patterns.
