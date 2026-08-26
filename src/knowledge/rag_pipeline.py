"""Phase 2.3 RAG pipeline prototype.

Implements a minimal retrieval augmented generation orchestration that:
query -> embeddings -> vector store -> context -> provider -> structured output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.knowledge.embedding import EmbeddingService
from src.knowledge.retriever import Retriever
from src.providers.registry import get_provider


class RAGPipeline:
    """Minimal RAG pipeline for the Phase 2.3 demonstration path.

    Returned structure is exactly:
    {
      "query": "",
      "sources": [],
      "context": "",
      "answer": "",
      "metadata": {}
    }
    """

    def __init__(self, vector_store: Any, provider_name: str = "mock"):
        self.vector_store = vector_store
        self.provider_name = provider_name
        self.embedding_service = EmbeddingService(provider_name)
        self.retriever = Retriever(vector_store, provider_name=provider_name)

    async def query(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Execute the complete RAG flow for a plain-text user question."""

        hits = await self.retriever.search(query, limit=limit)
        context = self.retriever.assemble_context(hits)

        provider = get_provider(self.provider_name)
        if hasattr(provider, "chat"):
            answer = await provider.chat(
                f"Use the supplied context to answer the query.\n\nQuery: {query}\n\nContext:\n{context}",
                query=query,
                context=context,
            )
        else:
            answer = context[:200]

        sources = []
        for hit in hits:
            sources.append({
                "chunk_id": hit.get("chunk_id"),
                "document_id": hit.get("document_id"),
                "score": hit.get("score"),
                "content": hit.get("content"),
                "metadata": hit.get("metadata", {}),
            })

        return {
            "query": query,
            "sources": sources,
            "context": context,
            "answer": answer,
            "metadata": {
                "provider": self.provider_name,
                "retrieval": "vector_similarity",
                "security": {
                    "permission_check": "available",
                    "source_tracking": "document_id",
                    "retrieval_audit": "enabled",
                },
                "hits": len(hits),
            },
        }
