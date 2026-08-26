"""Phase 2.2 knowledge chunker module.

Provides a lightweight document chunking abstraction that keeps the
existing repository patterns intact while exposing storage-friendly APIs
for the Embedding Pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Chunk:
    """Simple chunk container returned by the new knowledge chunker."""

    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """Simple deterministic chunker for text documents.

    Supports configurable chunk size and overlap while preserving metadata.
    """

    def __init__(self, chunk_size: int = 200, overlap: int = 20):
        self.chunk_size = max(1, chunk_size)
        self.overlap = max(0, overlap)

    def chunk_text(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Split text into overlapping text chunks.

        Returns a list of Chunk objects carrying a chunk_id and preserved
        metadata. The implementation favors simplicity and deterministic
        partitioning over a full NLP-aware chunker.
        """
        if not text or not text.strip():
            return []

        normalized_text = re.sub(r"\s+", " ", text.strip())
        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0
        while start < len(normalized_text):
            end = min(start + self.chunk_size, len(normalized_text))
            content = normalized_text[start:end]
            clean = content.strip()
            if clean:
                chunk = Chunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    content=clean,
                    chunk_index=chunk_index,
                    metadata=dict(metadata or {}),
                )
                chunks.append(chunk)
            chunk_index += 1
            if end == len(normalized_text):
                break
            start = max(start + self.chunk_size - self.overlap, end - self.overlap)

        return chunks


def chunk_text(
    document_id: str,
    text: str,
    chunk_size: int = 200,
    overlap: int = 20,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Chunk]:
    """Convenience wrapper around TextChunker.chunk_text."""

    return TextChunker(chunk_size=chunk_size, overlap=overlap).chunk_text(document_id, text, metadata)
