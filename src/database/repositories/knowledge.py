"""
Knowledge Repositories - Phase 2
Data access layer for Documents, Memory, and Company Brain
"""

from datetime import UTC, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    CompanyBrainEntityModel,
    CompanyBrainFactModel,
    DocumentChunkModel,
    DocumentModel,
    EmbeddingStorageModel,
    MemoryModel,
)
from src.database.repository import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    """Repository for Document operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentModel, session)

    async def search_by_title(self, query: str, limit: int = 20) -> List[DocumentModel]:
        """
        Search documents by title (case-insensitive)

        Args:
            query: Title search query
            limit: Maximum documents to return

        Returns:
            List of matching documents
        """
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.title.ilike(f"%{query}%"))
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_content(self, query: str, limit: int = 20) -> List[DocumentModel]:
        """
        Search documents by content (case-insensitive)

        Args:
            query: Content search query
            limit: Maximum documents to return

        Returns:
            List of matching documents
        """
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.content.ilike(f"%{query}%"))
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # Document lifecycle statuses that must never surface in retrieval:
    # failed uploads are marked "archived"/"failed", soft-deleted ones "deleted".
    _EXCLUDED_STATUSES = ("archived", "deleted", "failed")

    async def search_full_text(self, query: str, limit: int = 20) -> List[DocumentModel]:
        """
        Search documents by title or content

        Only live documents are returned; archived / failed / soft-deleted
        documents are excluded so a failed re-upload never leaves a searchable
        ghost row.

        Args:
            query: Search query
            limit: Maximum documents to return

        Returns:
            List of matching documents
        """
        result = await self.session.execute(
            select(DocumentModel)
            .where(
                or_(
                    DocumentModel.title.ilike(f"%{query}%"),
                    DocumentModel.content.ilike(f"%{query}%"),
                ),
                DocumentModel.status.notin_(self._EXCLUDED_STATUSES),
            )
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self,
        doc_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentModel]:
        """
        List documents by type

        Args:
            doc_type: Document type
            limit: Maximum documents to return
            offset: Number to skip

        Returns:
            List of documents
        """
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.doc_type == doc_type)
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_creator(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[DocumentModel]:
        """
        List documents by creator

        Args:
            user_id: Creator user ID
            limit: Maximum documents to return

        Returns:
            List of documents
        """
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.created_by == str(user_id))
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(self, days: int = 7, limit: int = 50) -> List[DocumentModel]:
        """
        List recently created documents

        Args:
            days: Number of days to look back
            limit: Maximum documents to return

        Returns:
            List of recent documents
        """
        since = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.created_at >= since)
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class MemoryRepository(BaseRepository[MemoryModel]):
    """Repository for Memory operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(MemoryModel, session)

    # Memory rows written with this user_id are shared agent experiences
    # (see MemoryService.store_agent_experience) and are visible to everyone.
    SHARED_MEMORY_USER_ID = "0"

    async def list_by_type(
        self,
        memory_type: str,
        limit: int = 100,
        offset: int = 0,
        scoped_user_id: Optional[str] = None,
    ) -> List[MemoryModel]:
        """
        List memories by type

        Args:
            memory_type: Memory type
            limit: Maximum memories to return
            offset: Number to skip
            scoped_user_id: When given, only return the owner's memories plus
                shared agent-experience rows (tenant/user isolation for
                cross-user knowledge search).

        Returns:
            List of memories (sorted by importance, then recency)
        """
        query = select(MemoryModel).where(MemoryModel.memory_type == memory_type)
        if scoped_user_id is not None:
            query = query.where(
                MemoryModel.user_id.in_(
                    [str(scoped_user_id), self.SHARED_MEMORY_USER_ID]
                )
            )
        result = await self.session.execute(
            query.order_by(MemoryModel.importance.desc(), MemoryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_recent(
        self, limit: int = 50, scoped_user_id: Optional[str] = None
    ) -> List[MemoryModel]:
        """
        List recent memories (by last accessed)

        Args:
            limit: Maximum memories to return
            scoped_user_id: When given, only return the owner's memories plus
                shared agent-experience rows (user isolation).

        Returns:
            List of recent memories
        """
        query = select(MemoryModel)
        if scoped_user_id is not None:
            query = query.where(
                MemoryModel.user_id.in_(
                    [str(scoped_user_id), self.SHARED_MEMORY_USER_ID]
                )
            )
        result = await self.session.execute(
            query.order_by(
                MemoryModel.last_accessed_at.desc().nulls_last(),
                MemoryModel.created_at.desc(),
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def list_important(
        self,
        min_importance: float = 0.7,
        limit: int = 50,
    ) -> List[MemoryModel]:
        """
        List important memories

        Args:
            min_importance: Minimum importance threshold (0.0-1.0)
            limit: Maximum memories to return

        Returns:
            List of important memories
        """
        result = await self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.importance >= min_importance)
            .order_by(MemoryModel.importance.desc(), MemoryModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_creator(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[MemoryModel]:
        """
        List memories by creator

        Args:
            user_id: Creator user ID
            limit: Maximum memories to return

        Returns:
            List of memories
        """
        result = await self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.created_by == str(user_id))
            .order_by(MemoryModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_access(self, memory_id: UUID):
        """
        Update memory access tracking

        Args:
            memory_id: Memory ID
        """
        await self.session.execute(select(MemoryModel).where(MemoryModel.id == str(memory_id)))
        memory = await self.get_by_id(memory_id)

        if memory:
            memory.last_accessed = datetime.now(UTC)
            memory.access_count += 1
            await self.session.flush()


class CompanyBrainEntityRepository(BaseRepository[CompanyBrainEntityModel]):
    """Repository for CompanyBrainEntity operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(CompanyBrainEntityModel, session)

    async def list_by_type(
        self,
        entity_type: str,
        limit: int = 100,
    ) -> List[CompanyBrainEntityModel]:
        """
        List entities by type

        Args:
            entity_type: Entity type
            limit: Maximum entities to return

        Returns:
            List of entities
        """
        result = await self.session.execute(
            select(CompanyBrainEntityModel)
            .where(CompanyBrainEntityModel.entity_type == entity_type)
            .order_by(CompanyBrainEntityModel.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_name(
        self, name_query: str, limit: int = 20
    ) -> List[CompanyBrainEntityModel]:
        """
        Search entities by name (case-insensitive)

        Args:
            name_query: Name search query
            limit: Maximum entities to return

        Returns:
            List of matching entities
        """
        result = await self.session.execute(
            select(CompanyBrainEntityModel)
            .where(CompanyBrainEntityModel.name.ilike(f"%{name_query}%"))
            .order_by(CompanyBrainEntityModel.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_related(
        self,
        entity_id: UUID,
        limit: int = 50,
    ) -> List[CompanyBrainEntityModel]:
        """
        List entities related to a specific entity

        Note: This requires parsing the relationships JSON field.
        For production, consider using a proper graph database.

        Args:
            entity_id: Entity ID
            limit: Maximum entities to return

        Returns:
            List of related entities
        """
        # Get the entity
        entity = await self.get_by_id(entity_id)

        if not entity or not entity.relationships:
            return []

        # Extract related entity IDs from relationships dict
        related_ids = list(entity.relationships.keys())

        if not related_ids:
            return []

        # Query related entities
        result = await self.session.execute(
            select(CompanyBrainEntityModel)
            .where(CompanyBrainEntityModel.id.in_(related_ids))
            .limit(limit)
        )
        return list(result.scalars().all())


class CompanyBrainFactRepository(BaseRepository[CompanyBrainFactModel]):
    """Repository for CompanyBrainFact operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(CompanyBrainFactModel, session)

    async def list_by_entity(
        self,
        entity_id: str,
        attribute: Optional[str] = None,
        active_only: bool = True,
    ) -> List[CompanyBrainFactModel]:
        """
        List facts for an entity

        Args:
            entity_id: Entity ID
            attribute: Optional filter by attribute name
            active_only: Only return active facts

        Returns:
            List of facts
        """

        conditions = [CompanyBrainFactModel.entity_id == entity_id]

        if attribute:
            conditions.append(CompanyBrainFactModel.attribute == attribute)

        if active_only:
            conditions.append(CompanyBrainFactModel.is_active)

        result = await self.session.execute(
            select(CompanyBrainFactModel)
            .where(and_(*conditions))
            .order_by(
                CompanyBrainFactModel.priority.desc(), CompanyBrainFactModel.created_at.desc()
            )
        )
        return list(result.scalars().all())

    async def deactivate_lower_priority_facts(
        self,
        entity_id: str,
        attribute: str,
        min_priority: int,
    ) -> int:
        """
        Deactivate facts with lower priority than threshold

        Args:
            entity_id: Entity ID
            attribute: Attribute name
            min_priority: Minimum priority threshold

        Returns:
            Number of facts deactivated
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(CompanyBrainFactModel)
            .where(
                and_(
                    CompanyBrainFactModel.entity_id == entity_id,
                    CompanyBrainFactModel.attribute == attribute,
                    CompanyBrainFactModel.priority < min_priority,
                    CompanyBrainFactModel.is_active,
                )
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self.session.commit()
        return result.rowcount


class DocumentChunkRepository(BaseRepository[DocumentChunkModel]):
    """Repository for DocumentChunk operations (Phase 2.2)."""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunkModel, session)

    async def list_by_document(self, document_id: str, limit: int = 1000) -> List[DocumentChunkModel]:
        result = await self.session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: str) -> int:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        )
        await self.session.commit()
        return result.rowcount


class EmbeddingStorageRepository(BaseRepository[EmbeddingStorageModel]):
    """Repository for EmbeddingStorage operations (Phase 2.2)."""

    def __init__(self, session: AsyncSession):
        super().__init__(EmbeddingStorageModel, session)

    async def find_by_document(self, document_id: str) -> List[EmbeddingStorageModel]:
        result = await self.session.execute(
            select(EmbeddingStorageModel)
            .where(EmbeddingStorageModel.document_id == document_id)
            .order_by(EmbeddingStorageModel.created_at)
        )
        return list(result.scalars().all())

    async def find_by_chunk(self, chunk_id: str) -> Optional[EmbeddingStorageModel]:
        result = await self.session.execute(
            select(EmbeddingStorageModel).where(EmbeddingStorageModel.chunk_id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        document_id: str,
        chunk_id: str,
        vector: List[float],
        provider: str,
        embedding_model: Optional[str] = None,
    ) -> EmbeddingStorageModel:
        from uuid import uuid4

        existing = await self.find_by_chunk(chunk_id)
        if existing:
            existing.vector = vector
            existing.dimension = len(vector)
            existing.provider = provider
            if embedding_model:
                existing.embedding_model = embedding_model
            await self.session.flush()
            return existing

        from datetime import UTC, datetime

        record = EmbeddingStorageModel(
            id=str(uuid4()),
            document_id=document_id,
            chunk_id=chunk_id,
            vector=vector,
            dimension=len(vector),
            provider=provider,
            embedding_model=embedding_model or "",
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def delete_by_document(self, document_id: str) -> int:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(EmbeddingStorageModel).where(EmbeddingStorageModel.document_id == document_id)
        )
        await self.session.commit()
        return result.rowcount
