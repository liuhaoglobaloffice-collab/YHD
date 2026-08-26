"""Phase 2.2 prototype vector store.

Provides a lightweight local SQLite-backed / in-memory abstraction for
persisting chunk embeddings and returning deterministic similarity results.
The implementation intentionally remains a prototype and keeps future PGVector
compatibility in mind by normalizing a consistent `insert/search/delete`
interface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass
class VectorRecord:
    """Persisted vector record descriptor."""

    chunk_id: str
    document_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class InMemoryVectorStore:
    """Prototype vector store with a local list of records.

    The interface deliberately mirrors the requested contract:
    insert(), search(), delete().
    """

    def __init__(self):
        self.records: List[VectorRecord] = []

    def insert(
        self,
        document_id: str,
        chunk_id: str,
        content: str,
        embedding: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist an embedding record for a given chunk."""

        record = VectorRecord(
            chunk_id=chunk_id,
            document_id=document_id,
            content=content,
            embedding=list(embedding),
            metadata=dict(metadata or {}),
        )
        self.records.append(record)
        return {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "status": "inserted",
            "metadata": dict(metadata or {}),
        }

    def search(self, embedding: Sequence[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Return vector similarity results from the local store.

        Uses a cosine-style similarity in a deterministic way so tests can
        compare the stored results without requiring a real vector DB.
        """

        query = list(embedding)
        if not query:
            return []

        results = []
        for record in self.records:
            score = self._similarity(query, record.embedding)
            if score < 0:
                score = 0.0
            results.append({
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "score": round(score, 4),
                "content": record.content,
                "metadata": dict(record.metadata),
            })

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def delete(self, document_id: Optional[str] = None, chunk_id: Optional[str] = None) -> int:
        """Delete stored entries by document_id or chunk_id."""

        if document_id is None and chunk_id is None:
            before = len(self.records)
            self.records.clear()
            return before

        remaining = []
        removed = 0
        for record in self.records:
            if document_id and record.document_id != document_id:
                remaining.append(record)
                continue
            if chunk_id and record.chunk_id != chunk_id:
                remaining.append(record)
                continue
            removed += 1
        self.records = remaining
        return removed

    @staticmethod
    def _similarity(left: Sequence[float], right: Sequence[float]) -> float:
        """Return a simple cosine-like similarity between two vectors."""

        if not left or not right:
            return 0.0
        max_len = max(len(left), len(right))
        left_pad = list(left) + [0.0] * max(0, max_len - len(left))
        right_pad = list(right) + [0.0] * max(0, max_len - len(right))
        numerator = sum(a * b for a, b in zip(left_pad, right_pad))
        left_norm = math.sqrt(sum(a * a for a in left_pad))
        right_norm = math.sqrt(sum(a * a for a in right_pad))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
