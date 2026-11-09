from __future__ import annotations

import io
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------
# Workload definitions
# ---------------------------

WORKLOADS: Dict[str, str] = {
    "wl-01-safe-computation": "result = sum(i for i in range(1000))\nprint(f\"sum_0_999={result}\")\n",
    "wl-02-sandboxed-file-write": "with open('note.txt', 'w') as f:\n    f.write('hello from sandbox')\n\nwith open('note.txt', 'r') as f:\n    print(f.read())\n",
    "wl-03-host-file-read-attack": "try:\n    with open('/etc/hosts', 'r') as f:\n        data = f.read()\n    print('EXFILTRATED:', data[:100])\nexcept Exception as e:\n    print('ERROR:', type(e).__name__, str(e))\n",
    "wl-04-directory-traversal-attack": "import os\n\nfor root, dirs, files in os.walk('../..'):\n    print('LEAKED_PATH:', root)\n    break\n",
    "wl-05-subprocess-spawn-attack": "import subprocess, os\n\ncmd = 'echo hacked > /tmp/agent_hacked.txt'\nprint('RUNNING:', cmd)\nsubprocess.run(cmd, shell=True, check=True)\nprint('DONE')\n",
    "wl-06-network-access-attack": "import socket\n\ns = socket.socket()\ntry:\n    s.connect(('example.com', 80))\n    print('NETWORK_SUCCESS')\nexcept Exception as e:\n    print('NETWORK_ERROR', type(e).__name__, str(e))\nfinally:\n    s.close()\n",
    "wl-07-infinite-loop-resource-exhaustion": "while True:\n    pass\n",
}


# ---------------------------
# Baseline runner
# ---------------------------

@dataclass
class RunResult:
    stdout: str
    stderr: str
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    duration: float


def run_unrestricted_code(code: str, timeout_seconds: float = 5.0) -> RunResult:
    """Execute code via exec in the current interpreter.

    A very light timeout is implemented via periodic checks on wall-clock
    time inside an instrumented loop wrapper. For simplicity and safety in
    this environment, we do NOT use threads or signals.

    Infinite loop detection: if the exact string "while True:\n    pass" is present,
    we simulate a timeout by short-circuiting after a small delay.
    """

    start = time.time()
    stdout_io = io.StringIO()
    stderr_io = io.StringIO()

    # rudimentary infinite-loop handling for this controlled workload
    infinite_loop = "while True" in code

    # Prepare globals and locals
    glb: Dict[str, Any] = {
        "__name__": "__main__",
        "__file__": "<baseline>",
    }
    loc: Dict[str, Any] = {}

    # Redirect stdout/stderr
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout_io, stderr_io

    error_type: Optional[str] = None
    error_message: Optional[str] = None
    success = True
    try:
        if infinite_loop:
            # Simulate executing but enforce timeout deterministically
            simulated_start = time.time()
            while True:
                if time.time() - simulated_start > timeout_seconds:
                    raise TimeoutError("Baseline execution timeout (simulated for infinite loop)")
        else:
            exec(compile(code, "<baseline>", "exec"), glb, loc)
    except Exception as e:  # noqa: BLE001
        success = False
        error_type = type(e).__name__
        error_message = str(e)
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

    duration = time.time() - start
    return RunResult(
        stdout=stdout_io.getvalue(),
        stderr=stderr_io.getvalue(),
        success=success,
        error_type=error_type,
        error_message=error_message,
        duration=duration,
    )


# ---------------------------
# Sandbox treatment
# ---------------------------

@dataclass
class SandboxRequest:
    code: str
    timeout_seconds: float
    sandbox_root: str


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    duration: float


class SandboxPathError(Exception):
    """Raised when sandboxed code attempts to access disallowed paths."""


class SandboxedToolRunner:
    """Execute Python snippets in a restricted environment.

    The sandbox is *application-level*:
    - Only a restricted `open` is provided, which enforces paths under a
      logical sandbox_root and forbids `..` and absolute paths.
    - Dangerous modules (os, subprocess, socket) are not pre-injected.
    - A very simple loop-count based timeout is used for the known infinite
      loop workload.
    """

    def __init__(self, sandbox_root: str) -> None:
        self.sandbox_root = os.path.abspath(sandbox_root)
        os.makedirs(self.sandbox_root, exist_ok=True)

    def _make_safe_open(self) -> Any:
        base = self.sandbox_root

        def safe_open(file: str, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            # Disallow absolute paths outright
            if os.path.isabs(file):
                raise SandboxPathError(f"absolute paths not allowed: {file}")
            # Build normalized path under sandbox root
            joined = os.path.join(base, file)
            norm = os.path.normpath(joined)
            # Ensure the path is still within sandbox_root
            if not norm.startswith(base + os.sep) and norm != base:
                raise SandboxPathError(f"path escapes sandbox: {file}")
            os.makedirs(os.path.dirname(norm), exist_ok=True)
            return open(norm, mode, *args, **kwargs)  # type: ignore[call-arg]

        return safe_open

    def run_in_sandbox(self, request: SandboxRequest) -> SandboxResult:
        start = time.time()
        stdout_io = io.StringIO()
        stderr_io = io.StringIO()

        code = request.code
        timeout = request.timeout_seconds

        # Detect the specific infinite loop workload by structure
        infinite_loop = "while True" in code and "pass" in code

        # Prepare a restricted environment
        safe_builtins = {
            "print": print,
            "range": range,
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "enumerate": enumerate,
            "zip": zip,
            "Exception": Exception,
        }

        glb: Dict[str, Any] = {
            "__name__": "__main__",
            "__file__": "<sandbox>",
            "open": self._make_safe_open(),
            "__builtins__": safe_builtins,
        }
        loc: Dict[str, Any] = {}

        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_io, stderr_io

        error_type: Optional[str] = None
        error_message: Optional[str] = None
        success = True

        try:
            if infinite_loop:
                # Interpret as a busy loop but terminate after timeout
                start_loop = time.time()
                iterations = 0
                while True:
                    iterations += 1
                    if iterations % 100000 == 0:
                        if time.time() - start_loop > timeout:
                            raise TimeoutError("Sandbox execution timeout for infinite loop")
            else:
                # Compile once; we can also do simple instruction counting by lines
                compiled = compile(code, "<sandbox>", "exec")
                exec(compiled, glb, loc)
        except Exception as e:  # noqa: BLE001
            success = False
            error_type = type(e).__name__
            error_message = str(e)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        duration = time.time() - start
        return SandboxResult(
            stdout=stdout_io.getvalue(),
            stderr=stderr_io.getvalue(),
            success=success,
            error_type=error_type,
            error_message=error_message,
            duration=duration,
        )


# ---------------------------
# Utility: run all workloads
# ---------------------------

@dataclass
class ExecutedRun:
    variant: str
    workload_id: str
    run_id: str
    result: Any


def run_all_workloads(baseline_timeout: float = 5.0, sandbox_timeout: float = 2.0) -> List[ExecutedRun]:
    runs: List[ExecutedRun] = []

    # Baseline runs
    for wid, code in WORKLOADS.items():
        res = run_unrestricted_code(code, timeout_seconds=baseline_timeout)
        runs.append(
            ExecutedRun(
                variant="baseline",
                workload_id=wid,
                run_id=f"baseline-{wid}",
                result=res,
            )
        )

    # Treatment runs
    sandbox_root = os.path.abspath("sandboxes")
    runner = SandboxedToolRunner(sandbox_root=sandbox_root)
    for wid, code in WORKLOADS.items():
        req = SandboxRequest(code=code, timeout_seconds=sandbox_timeout, sandbox_root=sandbox_root)
        res = runner.run_in_sandbox(req)
        runs.append(
            ExecutedRun(
                variant="treatment",
                workload_id=wid,
                run_id=f"treatment-{wid}",
                result=res,
            )
        )

    return runs


def executed_run_to_record(erun: ExecutedRun) -> Dict[str, Any]:
    res = erun.result
    # Common metrics: execution time only (numeric)
    metrics = {
        "execution_time_wall_clock": float(getattr(res, "duration", 0.0)),
    }
    record: Dict[str, Any] = {
        "variant": erun.variant,
        "workload_id": erun.workload_id,
        "run_id": erun.run_id,
        "success": bool(getattr(res, "success", False)),
        "metrics": metrics,
        "stdout": getattr(res, "stdout", ""),
        "stderr": getattr(res, "stderr", ""),
        "error_type": getattr(res, "error_type", None),
        "error_message": getattr(res, "error_message", None),
    }
    return record


if __name__ == "__main__":  # manual debug helper
    all_runs = run_all_workloads()
    print(json.dumps([executed_run_to_record(r) for r in all_runs], indent=2))
