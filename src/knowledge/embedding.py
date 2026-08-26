"""Phase 2.2 embedding service and embedding pipeline.

This module intentionally stays local and compatible with the repository's
provider registry patterns. It routes `embeddings()` calls via the
LLMProvider abstraction rather than directly depending on an external API
provider. The default and test-compatible provider selection is the existing
mock provider.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from src.providers.registry import get_provider
from src.knowledge.chunker import TextChunker, Chunk


class EmbeddingService:
    """Minimal deterministic embedding adapter.

    Resolves a provider from the existing registry, calls the provider's
    embeddings() method, and returns a vector sequence. Providers may be
    selected by registry alias (mock/openai/self_host).
    """

    def __init__(self, provider_name: str = "mock"):
        self.provider_name = provider_name
        self.provider = get_provider(provider_name)

    async def embed_text(self, text: str, **kwargs: Any) -> List[float]:
        if hasattr(self.provider, "embeddings"):
            return await self.provider.embeddings(text, **kwargs)
        raise TypeError("Configured provider does not implement embeddings()")

    async def embed_chunks(self, chunks: Sequence[Chunk]) -> List[Dict[str, Any]]:
        """Create an embedding for each chunk and return embedding descriptors."""

        rows: List[Dict[str, Any]] = []
        for chunk in chunks:
            vector = await self.embed_text(chunk.content)
            rows.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "vector": vector,
                "metadata": dict(chunk.metadata),
            })
        return rows


class EmbeddingPipeline:
    """Simple end-to-end pipeline for documents -> chunks -> embeddings -> vector store."""

    def __init__(
        self,
        vector_store: Any,
        provider_name: str = "mock",
        chunk_size: int = 200,
        overlap: int = 20,
    ):
        self.vector_store = vector_store
        self.provider_name = provider_name
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        self.embedding_service = EmbeddingService(provider_name)

    async def run(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process text into chunks, generate embeddings, and persist them.

        Returns a dictionary shaped like the requested acceptance payload:
        {
            document_id,
            chunks_count,
            embeddings_created,
            storage_status,
        }
        """

        chunks = self.chunker.chunk_text(document_id=document_id, text=text, metadata=metadata)
        stored = []
        for chunk in chunks:
            vector = await self.embedding_service.embed_text(chunk.content)
            inserted = self.vector_store.insert(
                document_id=document_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                embedding=vector,
                metadata=dict(chunk.metadata),
            )
            stored.append(inserted)

        return {
            "document_id": document_id,
            "chunks_count": len(chunks),
            "embeddings_created": len(stored),
            "storage_status": "ok" if stored else "empty",
        }

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_vector = await self.embedding_service.embed_text(query)
        return self.vector_store.search(query_vector, limit)
