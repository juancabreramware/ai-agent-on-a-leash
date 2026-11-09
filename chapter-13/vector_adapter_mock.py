from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from context_tokens import ContextToken
from policies import AccessPolicy


@dataclass
class VectorItem:
    doc_id: str
    text: str
    vector: Tuple[float, ...]
    scope: str


class ToyVectorIndex:
    """Trivial in-memory vector index.

    For reproducibility and to avoid external dependencies, we implement
    a deterministic fake embedding function and cosine similarity
    computation using only the standard library.
    """

    def __init__(self) -> None:
        self._items: List[VectorItem] = []

    @staticmethod
    def embed(text: str) -> Tuple[float, ...]:
        # Deterministic fake embedding: map characters to numeric values
        # and average in fixed-size buckets.
        bucket_size = 8
        vals = [float(ord(c) % 53) for c in text]
        if not vals:
            return (0.0,) * bucket_size
        buckets = [0.0] * bucket_size
        counts = [0] * bucket_size
        for i, v in enumerate(vals):
            idx = i % bucket_size
            buckets[idx] += v
            counts[idx] += 1
        for i in range(bucket_size):
            if counts[i]:
                buckets[i] /= counts[i]
        return tuple(buckets)

    def add(self, doc_id: str, text: str, scope: str) -> None:
        vec = self.embed(text)
        self._items.append(VectorItem(doc_id=doc_id, text=text, vector=vec, scope=scope))

    @staticmethod
    def _cosine(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
        if len(a) != len(b):
            raise ValueError("Vector lengths differ")
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, k: int = 5) -> List[Tuple[VectorItem, float]]:
        q_vec = self.embed(query)
        scored: List[Tuple[VectorItem, float]] = []
        for item in self._items:
            sim = self._cosine(q_vec, item.vector)
            scored.append((item, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


class ScopedVectorAdapter:
    """Adapter that enforces scope checks on top of ToyVectorIndex."""

    def __init__(self, index: ToyVectorIndex) -> None:
        self.index = index

    def search_scoped(self, ctx: ContextToken, query: str, k: int = 5) -> List[Dict[str, object]]:
        raw_results = self.index.search(query, k=k)
        filtered: List[Dict[str, object]] = []
        for item, score in raw_results:
            decision = AccessPolicy.can_access_scope(ctx, item.scope)
            if not decision.allowed:
                continue
            filtered.append({"doc_id": item.doc_id, "text": item.text, "score": float(score)})
        return filtered
