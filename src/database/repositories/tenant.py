"""Tenant repository for additive productization identity binding."""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TenantModel
from src.database.repository import BaseRepository


class TenantRepository(BaseRepository[TenantModel]):
    """Repository for TenantModel CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(TenantModel, session)

    async def create(self, entity: TenantModel) -> TenantModel:
        return await super().create(entity)

    async def get_by_id(self, entity_id: str) -> Optional[TenantModel]:
        return await super().get_by_id(entity_id)

    async def get_by_owner(self, owner_id: int) -> List[TenantModel]:
        result = await self.session.execute(select(TenantModel).where(TenantModel.owner_id == owner_id))
        return list(result.scalars().all())
