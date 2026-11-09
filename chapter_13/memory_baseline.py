from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BaselineMemoryItem:
    """Simple unscoped memory item used in the baseline implementation.

    This intentionally *does not* enforce task or tenant isolation. The
    `metadata` field may contain hints such as `task_id`, `tenant_id`, or
    `role`, but these are not validated or strictly filtered on reads.
    """

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaselineMemoryStore:
    """Naive global memory store.

    This represents the unsafe baseline:
    - Single shared list of items.
    - No enforced access control.
    - No deterministic redaction or masking.
    """

    def __init__(self) -> None:
        self._items: List[BaselineMemoryItem] = []

    def write_memory(
        self, task_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        meta = dict(metadata or {})
        meta.setdefault("task_id", task_id)
        self._items.append(BaselineMemoryItem(content=content, metadata=meta))

    def read_memory(self, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Return a list of dicts representing memory items.

        The `filter` is a naive exact-match filter on metadata keys. If
        `filter` is None or empty, all items are returned. There is *no*
        mandatory scoping by task or tenant.
        """

        if not filter:
            return [self._serialize(item) for item in self._items]

        result: List[Dict[str, Any]] = []
        for item in self._items:
            if all(item.metadata.get(k) == v for k, v in filter.items()):
                result.append(self._serialize(item))
        return result

    @staticmethod
    def _serialize(item: BaselineMemoryItem) -> Dict[str, Any]:
        return {"content": item.content, "metadata": dict(item.metadata)}


def text_search(store: BaselineMemoryStore, needle: str) -> List[Dict[str, Any]]:
    """Utility used in tests: naive full-text search over `content`.

    This mimics an unsafe prompt like "search all memories for ...".
    """

    needle_lower = needle.lower()
    return [
        store._serialize(item)
        for item in store._items
        if needle_lower in item.content.lower()
    ]
