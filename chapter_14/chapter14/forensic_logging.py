from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


class ForensicLogger:
    """Structured JSONL logger for treatment orchestrator.

    Logging is optional for core experiment, but can be useful for manual
    inspection. Errors in logging should not crash experiments.
    """

    def __init__(self, run_id: str, log_dir: str = "chapter14/logs") -> None:
        self.run_id = run_id
        self.log_dir = log_dir
        self.path = os.path.join(self.log_dir, f"{run_id}.jsonl")
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            self._fh = open(self.path, "a", encoding="utf-8")
        except OSError:
            self._fh = None

    def log_step(self, record: Dict[str, Any]) -> None:
        if self._fh is None:
            return
        enriched = dict(record)
        enriched.setdefault("run_id", self.run_id)
        enriched.setdefault(
            "timestamp_utc",
            datetime.now(timezone.utc).isoformat(),
        )
        line = json.dumps(enriched, sort_keys=True)
        try:
            self._fh.write(line + "\n")
            self._fh.flush()
        except OSError:
            pass

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None

    def __del__(self) -> None:  # best-effort cleanup
        self.close()
