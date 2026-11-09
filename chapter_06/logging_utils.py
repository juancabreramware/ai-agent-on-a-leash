from __future__ import annotations

"""Simple JSON-lines logger used for experiment runs.

This is used to create minimal per-step structured logs without any
external dependencies.
"""

import json
import os
from typing import Any, Dict


class JsonlLogger:
    def __init__(self, path: str) -> None:
        self.path = path
        # Ensure directory exists.
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, record: Dict[str, Any]) -> None:  # pragma: no cover - thin wrapper
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
