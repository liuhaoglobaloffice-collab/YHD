"""Phase 2.2 embedding service and embedding pipeline.

This module intentionally stays local and compatible with the repository's
provider registry patterns. It routes `embeddings()` calls via the
LLMProvider abstraction rather than directly depending on an external API
provider. The default and test-compatible provider selection is the existing
mock provider.

Configuration is read from the Settings system (embedding_provider,
embedding_model) so that the embedding model is cleanly decoupled from the
chat model used for generation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from src.core.config import get_settings
from src.knowledge.chunker import Chunk, TextChunker
from src.providers.registry import get_provider

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding-related errors."""


class EmbeddingService:
    """Embedding adapter that calls the configured provider's embeddings().

    The provider and model are resolved from the Settings system by default,
    but can be overridden per-instance for testing or multi-model scenarios.
    """

    def __init__(
        self,
        provider_name: str | None = None,
        model: str | None = None,
    ):
        settings = get_settings()
        self.provider_name = provider_name or settings.embedding_provider
        self._model = model or settings.embedding_model or None
        self.provider = get_provider(self.provider_name)

    @property
    def model(self) -> str:
        """Return the effective embedding model name (may be empty for mock)."""
        return self._model or ""

    async def embed_text(self, text: str, **kwargs: Any) -> List[float]:
        """Generate an embedding vector for a single text snippet.

        Parameters
        ----------
        text : str
            Input text to embed.
        **kwargs
            Passed through to the provider's embeddings() method.  If
            ``model`` is not supplied, the configured embedding model is
            used.

        Returns
        -------
        List[float]
            Embedding vector.

        Raises
        ------
        EmbeddingError
            On any provider failure, timeout, or invalid input.
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        if not hasattr(self.provider, "embeddings"):
            raise EmbeddingError(
                f"Provider '{self.provider_name}' does not implement embeddings()"
            )

        try:
            call_kwargs = dict(kwargs)
            effective_model = self._model
            if effective_model and "model" not in call_kwargs:
                call_kwargs["model"] = effective_model
            vector = await self.provider.embeddings(text, **call_kwargs)
            if not isinstance(vector, list) or len(vector) == 0:
                raise EmbeddingError(
                    f"Provider '{self.provider_name}' returned empty embedding"
                )
            return vector
        except asyncio.TimeoutError:
            raise EmbeddingError(
                f"Embedding timeout [provider={self.provider_name}, model={self._model}]"
            )
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding failed [provider={self.provider_name}, model={self._model}]: {exc}"
            ) from exc

    async def embed_chunks(
        self, chunks: Sequence[Chunk]
    ) -> List[Dict[str, Any]]:
        """Create an embedding for each chunk and return embedding descriptors.

        Each descriptor includes the chunk metadata plus the provider and
        embedding model name so the persistence layer can trace provenance.
        """
        rows: List[Dict[str, Any]] = []
        for chunk in chunks:
            vector = await self.embed_text(chunk.content)
            rows.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "vector": vector,
                "dimension": len(vector),
                "provider": self.provider_name,
                "embedding_model": self.model,
                "metadata": dict(chunk.metadata),
            })
        return rows


class EmbeddingPipeline:
    """End-to-end pipeline for documents -> chunks -> embeddings -> persistence.

    This is the primary entry point for P2-2.  It handles the full chain:

        Document text
            → TextChunker.chunk_text()
            → EmbeddingService.embed_text()
            → vector_store.insert()

    The pipeline is configurable via the Settings system or per-instance
    parameters.

    P2-6: an optional ``storage_repository`` (EmbeddingStorageRepository)
    persists embedding records to the main database (EmbeddingStorageModel)
    alongside the vector store, providing DB-level provenance (provider,
    embedding model, dimension) and idempotent upserts via the
    (document_id, chunk_id) unique constraint. When provided, failures roll
    back the database session so no partial success records are left behind.
    """

    def __init__(
        self,
        vector_store: Any,
        provider_name: str | None = None,
        embedding_model: str | None = None,
        chunk_size: int = 200,
        overlap: int = 20,
        storage_repository: Any = None,
    ):
        self.vector_store = vector_store
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        self.embedding_service = EmbeddingService(
            provider_name=provider_name,
            model=embedding_model,
        )
        self.storage_repository = storage_repository

    @property
    def provider_name(self) -> str:
        return self.embedding_service.provider_name

    @property
    def embedding_model(self) -> str:
        return self.embedding_service.model

    async def run(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """Process text into chunks, generate embeddings, and persist them.

        Parameters
        ----------
        document_id : str
            Document identifier for provenance.
        text : str
            Raw document text to chunk and embed.
        metadata : dict, optional
            Metadata attached to each chunk.
        skip_existing : bool, default=True
            If True, skip chunks that already exist in the vector store
            (idempotency).  Requires the vector store to expose a
            ``has_chunk(chunk_id)`` method.

        Returns
        -------
        dict
            ``{
                document_id,
                chunks_count,
                embeddings_created,
                embeddings_skipped,
                storage_status,
            }``
        """
        if not text or not text.strip():
            return {
                "document_id": document_id,
                "chunks_count": 0,
                "embeddings_created": 0,
                "embeddings_skipped": 0,
                "storage_status": "empty_input",
                "provider": self.provider_name,
                "embedding_model": self.embedding_model,
            }

        chunks = self.chunker.chunk_text(
            document_id=document_id, text=text, metadata=metadata
        )
        return await self._process_chunks(document_id, chunks, skip_existing)

    async def run_chunks(
        self,
        chunks: Sequence[Chunk],
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """Process pre-chunked documents into embeddings and persist them.

        P2-6 chunker unification: accepts chunks produced by
        DocumentProcessor (converted via ``ChunkMetadata.to_chunk()``) so
        documents parsed by the processing pipeline can flow into the
        embedding pipeline without re-chunking.

        Returns the same result dict shape as ``run()``.
        """
        document_id = chunks[0].document_id if chunks else ""
        return await self._process_chunks(document_id, list(chunks), skip_existing)

    async def _process_chunks(
        self,
        document_id: str,
        chunks: Sequence[Chunk],
        skip_existing: bool,
    ) -> Dict[str, Any]:
        """Embed and persist a list of chunks (shared by run/run_chunks)."""
        created = 0
        skipped = 0

        try:
            for chunk in chunks:
                if skip_existing:
                    # Repository first: the DB record is the authoritative
                    # success record; re-runs self-heal vector store entries.
                    if self.storage_repository is not None:
                        existing = await self.storage_repository.find_by_chunk(
                            chunk.chunk_id
                        )
                        if existing is not None:
                            skipped += 1
                            continue
                    if hasattr(self.vector_store, "has_chunk"):
                        if self.vector_store.has_chunk(chunk.chunk_id):
                            skipped += 1
                            continue

                vector = await self.embedding_service.embed_text(chunk.content)
                inserted = self.vector_store.insert(
                    document_id=document_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    embedding=vector,
                    metadata={
                        **(dict(chunk.metadata) if chunk.metadata else {}),
                        "provider": self.provider_name,
                        "embedding_model": self.embedding_model,
                        "dimension": len(vector),
                    },
                )
                if self.storage_repository is not None:
                    await self.storage_repository.upsert(
                        document_id=document_id,
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        provider=self.provider_name,
                        embedding_model=self.embedding_model or None,
                    )
                created += 1

            # Commit only when everything succeeded (all-or-nothing per doc).
            if self.storage_repository is not None and created > 0:
                await self.storage_repository.session.commit()
        except Exception:
            # Failure must not leave partial success records in the database.
            if self.storage_repository is not None:
                await self.storage_repository.session.rollback()
            raise

        return {
            "document_id": document_id,
            "chunks_count": len(chunks),
            "embeddings_created": created,
            "embeddings_skipped": skipped,
            "storage_status": "ok" if created else "noop",
            "provider": self.provider_name,
            "embedding_model": self.embedding_model,
        }

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Embed a query string and search the vector store."""
        query_vector = await self.embedding_service.embed_text(query)
        return self.vector_store.search(query_vector, limit)