"""
Knowledge Retrieval System

Unified retrieval layer for knowledge search.

P0-2: The service can be wired with database persistence:
- ``chunk_repository`` / ``embedding_repository`` / ``session`` enable
  durable chunk + embedding storage (DocumentChunkModel,
  EmbeddingStorageModel) through the existing EmbeddingPipeline.
- ``index_chunks_persisted()`` writes chunks + embeddings in one
  transaction: on embedding failure the whole batch is rolled back so
  no half-finished state survives.
- ``load_persisted()`` rebuilds the in-memory keyword index from the
  database after a process restart; embeddings are read from the
  persistent vector store (SQLiteVectorStore).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..core.errors import PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService
from .embedding import EmbeddingService, EmbeddingPipeline
from .processing import ChunkMetadata, ChunkType
from .vector_store import InMemoryVectorStore


class SearchMode(str, Enum):
    """Search mode"""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class SearchQuery:
    """Search query"""

    query: str
    mode: SearchMode = SearchMode.HYBRID

    # Filters
    document_ids: Optional[List[str]] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None

    # Pagination
    limit: int = 10
    offset: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result"""

    chunk: ChunkMetadata
    score: float
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
        }


class RetrievalService:
    """
    Retrieval Service

    Unified knowledge retrieval with hybrid search.
    """

    def __init__(
        self,
        rbac_service: RBACService,
        audit_service: AuditService,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[InMemoryVectorStore] = None,
        session=None,
        chunk_repository=None,
        embedding_repository=None,
    ):
        self.rbac = rbac_service
        self.audit = audit_service

        # In-memory keyword index (rebuilt from the database on load_persisted)
        self._chunks: Dict[str, ChunkMetadata] = {}
        self._inverted_index: Dict[str, List[str]] = {}
        self._document_owners: Dict[str, str] = {}
        self._document_visibility: Dict[str, str] = {}

        # Embedding & vector store for semantic search.
        # P0-2: production wiring passes a persistent SQLiteVectorStore.
        # The embedding provider follows Settings (embedding_provider),
        # so .env configuration is respected (mock/openai/self_host).
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_store = vector_store or InMemoryVectorStore()
        self._embeddings_indexed: bool = False

        # P0-2: database persistence (chunks + embeddings)
        self.session = session
        self.chunk_repository = chunk_repository
        self.embedding_repository = embedding_repository
        self._restored: bool = False

    def index_chunk(self, chunk: ChunkMetadata) -> None:
        """
        Index a chunk

        Args:
            chunk: Chunk to index
        """
        # Store chunk
        self._chunks[chunk.chunk_id] = chunk

        # Track document ownership
        document_id = chunk.document_id
        if document_id not in self._document_owners:
            # Extract owner from metadata if available, otherwise leave as None
            owner_id = chunk.metadata.get("owner_id")
            if owner_id:
                self._document_owners[document_id] = str(owner_id)

        # Build inverted index (keyword search)
        words = self._tokenize(chunk.content)
        for word in words:
            if word not in self._inverted_index:
                self._inverted_index[word] = []
            if chunk.chunk_id not in self._inverted_index[word]:
                self._inverted_index[word].append(chunk.chunk_id)

    def register_document_owner(
        self, document_id: str, owner_id: str, visibility: str = "private"
    ) -> None:
        """
        Register document ownership for permission filtering.

        Args:
            document_id: Document ID
            owner_id: User ID who owns this document
            visibility: Visibility level - 'private', 'team', or 'public'
        """
        self._document_owners[document_id] = owner_id
        self._document_visibility[document_id] = visibility

    async def _ensure_embeddings(self) -> None:
        """
        Lazily generate embeddings for all indexed chunks using the real
        EmbeddingService and store them in the vector store.

        This runs once on first semantic/hybrid search; subsequent calls
        are no-ops.
        """
        if self._embeddings_indexed:
            return

        if not self._chunks:
            self._embeddings_indexed = True
            return

        for chunk in self._chunks.values():
            vector = await self._embedding_service.embed_text(chunk.content)
            self._vector_store.insert(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                embedding=vector,
                metadata=chunk.metadata,
            )

        self._embeddings_indexed = True

    def _can_access_document(self, user: User, document_id: str) -> bool:
        """
        Check if user can access a document based on ownership and visibility.

        Args:
            user: User requesting access
            document_id: Document ID to check

        Returns:
            True if user can access the document
        """
        # Public documents are accessible to everyone
        visibility = self._document_visibility.get(document_id, "private")
        if visibility == "public":
            return True

        # Check if user is the owner
        owner_id = self._document_owners.get(document_id)
        if owner_id and str(user.id) == owner_id:
            return True

        # Team documents: accessible if user has KNOWLEDGE_READ permission
        if visibility == "team":
            return self.rbac.has_permission(user, Permission.KNOWLEDGE_READ)

        # Private documents: only owner can access
        return False

    def index_chunks(self, chunks: List[ChunkMetadata]) -> None:
        """
        Index multiple chunks

        Args:
            chunks: Chunks to index
        """
        for chunk in chunks:
            self.index_chunk(chunk)

    # ------------------------------------------------------------------
    # P0-2: Database persistence (chunks + embeddings)
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_meta_json(chunk: ChunkMetadata) -> Dict[str, Any]:
        """Serialize chunk metadata for DocumentChunkModel.metadata_."""
        reserved = {"owner_id", "visibility"}
        custom = {k: v for k, v in (chunk.metadata or {}).items() if k not in reserved}
        return {
            "chunk_type": chunk.chunk_type.value,
            "document_version": chunk.document_version,
            "page": chunk.page,
            "section": chunk.section,
            "sheet": chunk.sheet,
            "token_count": chunk.token_count,
            "char_count": chunk.char_count,
            "owner_id": (chunk.metadata or {}).get("owner_id"),
            "visibility": (chunk.metadata or {}).get("visibility", "private"),
            "custom": custom,
        }

    @staticmethod
    def _model_to_chunk(model) -> ChunkMetadata:
        """Convert DocumentChunkModel back to ChunkMetadata."""
        meta = dict(model.metadata_ or {})
        chunk_meta = dict(meta.get("custom", {}))
        if meta.get("owner_id"):
            chunk_meta["owner_id"] = meta["owner_id"]
        if meta.get("visibility"):
            chunk_meta["visibility"] = meta["visibility"]
        return ChunkMetadata(
            chunk_id=str(model.id),
            document_id=model.document_id,
            document_version=meta.get("document_version", 1),
            chunk_index=model.chunk_index,
            chunk_type=ChunkType(meta.get("chunk_type", ChunkType.PARAGRAPH.value)),
            content=model.chunk_text,
            page=meta.get("page"),
            section=meta.get("section"),
            sheet=meta.get("sheet"),
            token_count=meta.get("token_count", 0),
            char_count=meta.get("char_count", len(model.chunk_text)),
            metadata=chunk_meta,
        )

    async def index_chunks_persisted(self, chunks: List[ChunkMetadata]) -> Dict[str, Any]:
        """
        Index chunks in memory AND persist them (chunks + embeddings) to
        the database in a single transaction.

        Transaction semantics: chunk rows and EmbeddingStorageModel rows
        share one session. The EmbeddingPipeline commits on success and
        rolls back on failure — an embedding failure therefore discards
        the chunk rows too, leaving no half-finished state.

        Idempotency: re-indexing the same document replaces its chunk /
        embedding / vector records (no unbounded duplicates).

        Returns:
            dict: EmbeddingPipeline result
                {document_id, chunks_count, embeddings_created,
                 embeddings_skipped, storage_status, provider,
                 embedding_model}

        Raises:
            ValidationError: If persistence is not configured
        """
        if self.session is None or self.chunk_repository is None:
            raise ValidationError(
                "RetrievalService is not configured with database persistence"
            )
        if not chunks:
            return {
                "document_id": "",
                "chunks_count": 0,
                "embeddings_created": 0,
                "embeddings_skipped": 0,
                "storage_status": "noop",
            }

        document_id = chunks[0].document_id

        # 1. In-memory keyword index (immediate searchability)
        self.index_chunks(chunks)

        from sqlalchemy import delete as sa_delete

        from ..database.models import DocumentChunkModel, EmbeddingStorageModel

        # 2. Replace persisted chunks for this document (idempotent re-index)
        await self.session.execute(
            sa_delete(DocumentChunkModel).where(
                DocumentChunkModel.document_id == document_id
            )
        )
        await self.session.execute(
            sa_delete(EmbeddingStorageModel).where(
                EmbeddingStorageModel.document_id == document_id
            )
        )
        for chunk in chunks:
            self.session.add(
                DocumentChunkModel(
                    id=chunk.chunk_id,
                    document_id=document_id,
                    chunk_text=chunk.content,
                    chunk_index=chunk.chunk_index,
                    metadata_=self._chunk_meta_json(chunk),
                )
            )
        await self.session.flush()

        # 3. Drop stale vector entries before re-embedding
        self._vector_store.delete(document_id=document_id)

        # 4. Embeddings via the existing pipeline: commits on success,
        #    rolls back (chunks included) on failure.
        pipeline = EmbeddingPipeline(
            vector_store=self._vector_store,
            provider_name=self._embedding_service.provider_name,
            storage_repository=self.embedding_repository,
        )
        result = await pipeline.run_chunks([c.to_chunk() for c in chunks])

        # The pipeline already embedded + inserted every chunk into the
        # vector store; mark embeddings ready so _ensure_embeddings()
        # does not re-embed everything on the next search.
        self._embeddings_indexed = True
        return result

    async def load_persisted(self) -> int:
        """
        Restore the in-memory index from persisted chunks (restart recovery).

        Reads DocumentChunkModel rows, rebuilds the keyword index and
        document ownership/visibility maps. Embeddings are NOT regenerated:
        they live in the persistent vector store (SQLiteVectorStore).

        Returns:
            int: Number of chunks restored
        """
        if self.chunk_repository is None or self.session is None:
            return 0

        from ..database.models import DocumentChunkModel

        result = await self.session.execute(
            select(DocumentChunkModel).order_by(
                DocumentChunkModel.document_id, DocumentChunkModel.chunk_index
            )
        )
        models = list(result.scalars().all())

        for model in models:
            chunk = self._model_to_chunk(model)
            self.index_chunk(chunk)

            meta = dict(model.metadata_ or {})
            owner_id = meta.get("owner_id")
            if owner_id:
                self._document_owners[model.document_id] = str(owner_id)
                self._document_visibility[model.document_id] = meta.get(
                    "visibility", "private"
                )

        # Embeddings already live in the persistent vector store
        if self._vector_store.records:
            self._embeddings_indexed = True

        self._restored = True
        return len(models)

    async def remove_document_chunks_persisted(self, document_id: str) -> int:
        """
        Remove a document's chunks from memory, the database, and the
        vector store (full cleanup).

        Returns:
            int: Number of in-memory chunks removed
        """
        if self.session is not None:
            from sqlalchemy import delete as sa_delete

            from ..database.models import DocumentChunkModel, EmbeddingStorageModel

            await self.session.execute(
                sa_delete(DocumentChunkModel).where(
                    DocumentChunkModel.document_id == document_id
                )
            )
            await self.session.execute(
                sa_delete(EmbeddingStorageModel).where(
                    EmbeddingStorageModel.document_id == document_id
                )
            )
            await self.session.commit()

        self._vector_store.delete(document_id=document_id)
        return self.remove_document_chunks(document_id)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for keyword search"""
        # Simple tokenization: lowercase and split by non-alphanumeric
        import re

        words = re.findall(r"\w+", text.lower())
        return [w for w in words if len(w) > 2]  # Filter short words

    async def search(
        self,
        user: User,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """
        Search knowledge base

        Args:
            user: User performing the search
            query: Search query

        Returns:
            List[SearchResult]: Search results

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="search_knowledge",
                resource_type="knowledge",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Validate query
        if not query.query or len(query.query.strip()) == 0:
            raise ValidationError("Search query cannot be empty")

        # Execute search based on mode
        if query.mode == SearchMode.KEYWORD:
            results = self._keyword_search(user, query)
        elif query.mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(user, query)
        else:  # HYBRID
            results = await self._hybrid_search(user, query)

        # Apply pagination
        paginated = results[query.offset : query.offset + query.limit]

        # Audit log
        await self.audit.log(
            action=AuditAction.READ,
            user_id=user.id,
            resource_type="knowledge",
            details={
                "query": query.query,
                "mode": query.mode.value,
                "results_count": len(paginated),
            },
        )

        return paginated

    def _keyword_search(
        self,
        user: User,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """Keyword-based search"""
        # Tokenize query
        query_words = self._tokenize(query.query)

        # Find matching chunks
        chunk_scores: Dict[str, float] = {}

        for word in query_words:
            if word in self._inverted_index:
                for chunk_id in self._inverted_index[word]:
                    chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + 1

        # Filter by permissions and query filters
        results = []
        for chunk_id, score in chunk_scores.items():
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue

            # Apply filters
            if query.document_ids and chunk.document_id not in query.document_ids:
                continue
            if query.owner_id and self._document_owners.get(chunk.document_id) != query.owner_id:
                continue

            # Permission filtering: check document ownership/visibility
            if not self._can_access_document(user, chunk.document_id):
                continue

            # Create result
            highlights = self._extract_highlights(chunk.content, query_words)
            result = SearchResult(
                chunk=chunk,
                score=score,
                highlights=highlights,
            )
            results.append(result)

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        return results

    async def _semantic_search(
        self,
        user: User,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """
        Semantic search (vector-based)

        Uses the project's existing EmbeddingService + InMemoryVectorStore
        to generate real embeddings and perform vector similarity search.
        Falls back to keyword search if vector search is unavailable.
        """
        try:
            # Ensure embeddings are generated (lazy, once)
            await self._ensure_embeddings()

            # Build a per-query vector store filtered by access + filters
            filtered_store = InMemoryVectorStore()
            for record in self._vector_store.records:
                chunk = self._chunks.get(record.chunk_id)
                if not chunk:
                    continue
                # Permission filtering
                if not self._can_access_document(user, chunk.document_id):
                    continue
                # Apply explicit document filter
                if query.document_ids and chunk.document_id not in query.document_ids:
                    continue
                if query.owner_id and self._document_owners.get(chunk.document_id) != query.owner_id:
                    continue
                filtered_store.insert(
                    document_id=record.document_id,
                    chunk_id=record.chunk_id,
                    content=record.content,
                    embedding=record.embedding,
                    metadata=record.metadata,
                )

            # Embed the query using the same EmbeddingService
            query_vector = await self._embedding_service.embed_text(query.query)
            hits = filtered_store.search(query_vector, limit=query.limit + query.offset)

            # Convert to SearchResult
            query_words = self._tokenize(query.query)
            results = []
            for hit in hits:
                chunk = self._chunks.get(hit.get("chunk_id", ""))
                if not chunk:
                    continue
                highlights = self._extract_highlights(chunk.content, query_words)
                results.append(
                    SearchResult(
                        chunk=chunk,
                        score=hit.get("score", 0.0),
                        highlights=highlights,
                    )
                )
            return results

        except Exception:
            # Fall back to keyword search on any error
            return self._keyword_search(user, query)

    async def _hybrid_search(
        self,
        user: User,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """
        Hybrid search (keyword + semantic)

        Note: This combines keyword and semantic search results.
        """
        # Get keyword results
        keyword_results = self._keyword_search(user, query)

        # Get semantic results (vector-based)
        semantic_results = await self._semantic_search(user, query)

        # Merge results (simple approach: deduplicate and re-rank)
        result_map: Dict[str, SearchResult] = {}

        for result in keyword_results:
            result_map[result.chunk.chunk_id] = result

        for result in semantic_results:
            chunk_id = result.chunk.chunk_id
            if chunk_id in result_map:
                # Combine scores
                result_map[chunk_id].score += result.score
            else:
                result_map[chunk_id] = result

        # Sort by combined score
        results = list(result_map.values())
        results.sort(key=lambda r: r.score, reverse=True)

        return results

    def _extract_highlights(
        self,
        content: str,
        query_words: List[str],
        context_size: int = 100,
    ) -> List[str]:
        """Extract highlighted snippets from content"""
        highlights = []
        content_lower = content.lower()

        for word in query_words:
            # Find word positions
            start = 0
            while True:
                pos = content_lower.find(word, start)
                if pos == -1:
                    break

                # Extract context
                snippet_start = max(0, pos - context_size)
                snippet_end = min(len(content), pos + len(word) + context_size)
                snippet = content[snippet_start:snippet_end]

                # Add ellipsis
                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(content):
                    snippet = snippet + "..."

                highlights.append(snippet)
                start = pos + len(word)

                # Limit highlights per word
                if len(highlights) >= 3:
                    break

            if len(highlights) >= 3:
                break

        return highlights

    async def get_chunk(
        self,
        user: User,
        chunk_id: str,
    ) -> ChunkMetadata:
        """
        Get chunk by ID

        Args:
            user: User requesting the chunk
            chunk_id: Chunk ID

        Returns:
            ChunkMetadata: Chunk metadata

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="get_chunk",
                resource_type="knowledge",
                resource_id=chunk_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        chunk = self._chunks.get(chunk_id)
        if not chunk:
            raise ValidationError(f"Chunk not found: {chunk_id}")

        # Audit log
        await self.audit.log(
            action=AuditAction.READ,
            user_id=user.id,
            resource_type="knowledge",
            resource_id=chunk_id,
        )

        return chunk

    def remove_document_chunks(self, document_id: str) -> int:
        """
        Remove all chunks for a document

        Args:
            document_id: Document ID

        Returns:
            int: Number of chunks removed
        """
        removed = 0
        chunk_ids_to_remove = []

        # Find chunks to remove
        for chunk_id, chunk in self._chunks.items():
            if chunk.document_id == document_id:
                chunk_ids_to_remove.append(chunk_id)

        # Remove chunks
        for chunk_id in chunk_ids_to_remove:
            del self._chunks[chunk_id]
            removed += 1

            # Remove from inverted index
            for word, chunk_list in self._inverted_index.items():
                if chunk_id in chunk_list:
                    chunk_list.remove(chunk_id)

        # Clean up ownership tracking
        if document_id in self._document_owners:
            del self._document_owners[document_id]
        if document_id in self._document_visibility:
            del self._document_visibility[document_id]

        # Also remove from vector store
        if removed > 0:
            self._vector_store.delete(document_id=document_id)

        return removed
