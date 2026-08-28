"""Enterprise repository for additive productization identity binding."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import EnterpriseModel
from src.database.repository import BaseRepository


class EnterpriseRepository(BaseRepository[EnterpriseModel]):
    """Repository for EnterpriseModel CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(EnterpriseModel, session)

    async def create(self, entity: EnterpriseModel) -> EnterpriseModel:
        return await super().create(entity)

    async def get_by_id(self, entity_id: str) -> Optional[EnterpriseModel]:
        return await super().get_by_id(entity_id)
