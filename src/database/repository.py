"""
Repository Pattern - Phase 2
Base repository with common CRUD operations

Repository Pattern Benefits:
- Clean separation of data access and business logic
- Easy to test (mock repositories)
- Single source of truth for data operations
- Transaction management
- Type safety
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Generic type for SQLAlchemy models
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations

    Usage:
        class WorkflowRepository(BaseRepository[WorkflowModel]):
            def __init__(self, session: AsyncSession):
                super().__init__(WorkflowModel, session)

            async def list_by_creator(self, user_id: UUID) -> List[WorkflowModel]:
                result = await self.session.execute(
                    select(self.model_class)
                    .where(self.model_class.created_by == str(user_id))
                )
                return list(result.scalars().all())
    """

    def __init__(self, model_class: type[T], session: AsyncSession):
        """
        Initialize repository

        Args:
            model_class: SQLAlchemy model class
            session: Database session
        """
        self.model_class = model_class
        self.session = session
        self.logger = logger.bind(repository=model_class.__name__)

    async def create(self, entity: T) -> T:
        """
        Create new entity

        Args:
            entity: Entity to create

        Returns:
            Created entity with ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)

        self.logger.info(
            "entity_created",
            entity_id=getattr(entity, "id", None),
        )

        return entity

    async def get_by_id(self, entity_id: str | UUID) -> Optional[T]:
        """
        Get entity by ID

        Args:
            entity_id: Entity ID (UUID or string)

        Returns:
            Entity if found, None otherwise
        """
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == str(entity_id))
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        List all entities with pagination

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        result = await self.session.execute(
            select(self.model_class).limit(limit).offset(offset).order_by(self.model_class.id)
        )
        return list(result.scalars().all())

    async def update(self, entity_id: str | UUID, values: Dict[str, Any]) -> Optional[T]:
        """
        Update entity by ID

        Args:
            entity_id: Entity ID
            values: Dictionary of field:value pairs to update

        Returns:
            Updated entity if found, None otherwise
        """
        await self.session.execute(
            update(self.model_class).where(self.model_class.id == str(entity_id)).values(**values)
        )
        await self.session.flush()

        self.logger.info(
            "entity_updated",
            entity_id=str(entity_id),
            fields=list(values.keys()),
        )

        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: str | UUID) -> bool:
        """
        Delete entity by ID

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == str(entity_id))
        )
        await self.session.flush()

        deleted = result.rowcount > 0

        if deleted:
            self.logger.info("entity_deleted", entity_id=str(entity_id))
        else:
            self.logger.warning("entity_not_found_for_delete", entity_id=str(entity_id))

        return deleted

    async def exists(self, entity_id: str | UUID) -> bool:
        """
        Check if entity exists

        Args:
            entity_id: Entity ID

        Returns:
            True if exists, False otherwise
        """
        result = await self.session.execute(
            select(self.model_class.id).where(self.model_class.id == str(entity_id))
        )
        return result.scalar_one_or_none() is not None

    async def count(self, **filters) -> int:
        """
        Count entities with optional filters

        Args:
            **filters: Column filters (e.g., status="active")

        Returns:
            Count of entities
        """
        query = select(func.count()).select_from(self.model_class)

        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.where(getattr(self.model_class, key) == value)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def list_by_field(
        self,
        field_name: str,
        field_value: Any,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """
        List entities by a specific field value

        Args:
            field_name: Field name to filter by
            field_value: Field value to match
            limit: Maximum number of entities
            offset: Number of entities to skip

        Returns:
            List of matching entities
        """
        if not hasattr(self.model_class, field_name):
            raise ValueError(f"Model {self.model_class.__name__} has no field '{field_name}'")

        result = await self.session.execute(
            select(self.model_class)
            .where(getattr(self.model_class, field_name) == field_value)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def commit(self):
        """Commit current transaction"""
        await self.session.commit()
        self.logger.debug("transaction_committed")

    async def rollback(self):
        """Rollback current transaction"""
        await self.session.rollback()
        self.logger.warning("transaction_rolled_back")

    async def refresh(self, entity: T) -> T:
        """
        Refresh entity from database

        Args:
            entity: Entity to refresh

        Returns:
            Refreshed entity
        """
        await self.session.refresh(entity)
        return entity
