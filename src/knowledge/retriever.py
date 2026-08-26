"""Phase 2.3 Retriever and vector search adapter.

Provides a minimal RAG retrieval orientation on top of the existing
Phase 2.2 vector store prototype and provider registry abstraction.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.providers.registry import get_provider
from src.knowledge.embedding import EmbeddingService
from src.knowledge.vector_store import InMemoryVectorStore


class Retriever:
    """Vector retriever built on the Phase 2.2 embedding and vector store pattern."""

    def __init__(self, vector_store: Any, provider_name: str = "mock", limit: int = 5):
        self.vector_store = vector_store
        self.provider_name = provider_name
        self.limit = limit
        self.embedding_service = EmbeddingService(provider_name)

    async def search(self, query: str, limit: int = 5, document_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Embed the query and retrieve the most relevant vector records.

        Returns a normalized list containing the vector store's search payloads
        plus a deterministic `score` ranking already returned from the store.
        """

        query_vector = await self.embedding_service.embed_text(query)
        hits = self.vector_store.search(query_vector, limit=limit)

        # document_filter is an optional boundary for future document ownership
        # enforcement and source tracking, without forcing a larger permission engine.
        if document_filter:
            hits = [hit for hit in hits if hit.get("document_id") == document_filter]

        for hit in hits:
            hit.setdefault("sources", [hit.get("document_id")])
            hit.setdefault("metadata", {})
            hit["metadata"].setdefault("provider", self.provider_name)
            hit["metadata"].setdefault("retrieval_policy", "vector_similarity")

        return hits

    def assemble_context(self, hits: Sequence[Dict[str, Any]]) -> str:
        """Turn a hit list into a deterministic context string for LLM prompting."""

        statements = []
        for item in hits:
            content = str(item.get("content") or "").strip()
            if content:
                statements.append(content)
        return "\n".join(statements)
