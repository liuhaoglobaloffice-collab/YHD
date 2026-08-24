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
    DocumentModel,
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

    async def search_full_text(self, query: str, limit: int = 20) -> List[DocumentModel]:
        """
        Search documents by title or content

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
                )
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

    async def list_by_type(
        self,
        memory_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryModel]:
        """
        List memories by type

        Args:
            memory_type: Memory type
            limit: Maximum memories to return
            offset: Number to skip

        Returns:
            List of memories (sorted by importance, then recency)
        """
        result = await self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.memory_type == memory_type)
            .order_by(MemoryModel.importance.desc(), MemoryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> List[MemoryModel]:
        """
        List recent memories (by last accessed)

        Args:
            limit: Maximum memories to return

        Returns:
            List of recent memories
        """
        result = await self.session.execute(
            select(MemoryModel)
            .order_by(
                MemoryModel.last_accessed_at.desc().nulls_last(), MemoryModel.created_at.desc()
            )
            .limit(limit)
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
