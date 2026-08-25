"""
Knowledge Retrieval System

Unified retrieval layer for knowledge search.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.errors import PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService
from .processing import ChunkMetadata


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
    ):
        self.rbac = rbac_service
        self.audit = audit_service

        # In-memory storage (will be replaced with vector store)
        self._chunks: Dict[str, ChunkMetadata] = {}
        self._inverted_index: Dict[str, List[str]] = {}

    def index_chunk(self, chunk: ChunkMetadata) -> None:
        """
        Index a chunk

        Args:
            chunk: Chunk to index
        """
        # Store chunk
        self._chunks[chunk.chunk_id] = chunk

        # Build inverted index (keyword search)
        words = self._tokenize(chunk.content)
        for word in words:
            if word not in self._inverted_index:
                self._inverted_index[word] = []
            if chunk.chunk_id not in self._inverted_index[word]:
                self._inverted_index[word].append(chunk.chunk_id)

    def index_chunks(self, chunks: List[ChunkMetadata]) -> None:
        """
        Index multiple chunks

        Args:
            chunks: Chunks to index
        """
        for chunk in chunks:
            self.index_chunk(chunk)

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
            results = self._semantic_search(user, query)
        else:  # HYBRID
            results = self._hybrid_search(user, query)

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

            # TODO: Check document ownership/permissions
            # For now, simple check

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

    def _semantic_search(
        self,
        user: User,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """
        Semantic search (vector-based)

        Note: This requires embedding model and vector store.
        For Stage 4, we provide a placeholder implementation.
        """
        # TODO: Implement with embedding model + vector store
        # For now, fall back to keyword search
        return self._keyword_search(user, query)

    def _hybrid_search(
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

        # Get semantic results (currently same as keyword)
        semantic_results = self._semantic_search(user, query)

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

        return removed
