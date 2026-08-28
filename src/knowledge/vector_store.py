"""Phase 2.2 prototype vector store.

Provides a lightweight local SQLite-backed / in-memory abstraction for
persisting chunk embeddings and returning deterministic similarity results.
The implementation intentionally remains a prototype and keeps future PGVector
compatibility in mind by normalizing a consistent `insert/search/delete`
interface.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
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


class SQLiteVectorStore:
    """SQLite-persisted vector store with the same insert/search/delete contract.

    Embeds are stored in a local SQLite file so knowledge and RAG data survives
    process restarts (unlike the pure in-memory variant). Uses a per-instance
    connection guarded by a lock; safe for the lightweight prototype workload.
    """

    def __init__(self, db_path: str = "./data/knowledge_vectors.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vector_chunk ON vector_records(chunk_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vector_doc ON vector_records(document_id)"
            )
            conn.commit()

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def records(self) -> List[VectorRecord]:
        """Materialize all persisted records as VectorRecord objects."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT chunk_id, document_id, content, embedding, metadata "
                "FROM vector_records ORDER BY id"
            ).fetchall()
        records = []
        for row in rows:
            try:
                embedding = json.loads(row["embedding"])
            except (json.JSONDecodeError, TypeError):
                embedding = []
            try:
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            records.append(
                VectorRecord(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    content=row["content"],
                    embedding=embedding,
                    metadata=metadata,
                )
            )
        return records

    def insert(
        self,
        document_id: str,
        chunk_id: str,
        content: str,
        embedding: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist an embedding record for a given chunk."""
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vector_records "
                "(chunk_id, document_id, content, embedding, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    chunk_id,
                    document_id,
                    content,
                    json.dumps(list(embedding)),
                    json.dumps(metadata, ensure_ascii=False) if metadata else "{}",
                ),
            )
            conn.commit()
        return {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "status": "inserted",
            "metadata": dict(metadata or {}),
        }

    def search(self, embedding: Sequence[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Return vector similarity results from the persisted store."""
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
        with self._lock, self._connect() as conn:
            if document_id is None and chunk_id is None:
                cur = conn.execute("DELETE FROM vector_records")
            elif document_id is not None and chunk_id is not None:
                cur = conn.execute(
                    "DELETE FROM vector_records WHERE document_id = ? AND chunk_id = ?",
                    (document_id, chunk_id),
                )
            elif document_id is not None:
                cur = conn.execute(
                    "DELETE FROM vector_records WHERE document_id = ?", (document_id,)
                )
            else:
                cur = conn.execute(
                    "DELETE FROM vector_records WHERE chunk_id = ?", (chunk_id,)
                )
            conn.commit()
            return cur.rowcount

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
