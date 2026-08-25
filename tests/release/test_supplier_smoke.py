import os

os.environ.setdefault("SECRET_KEY", "1234567890abcdef1234567890abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "1234567890abcdef1234567890abcdef")

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import BusinessType, SupplierStatus
from src.database.base import Base


async def _supplier_smoke():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        crud = SupplierCRUD(session)
        supplier = await crud.create_supplier(
            name="Release Supplier",
            country="China",
            product_category="Industrial Components",
            code="SUP9999",
            business_type=BusinessType.MANUFACTURER,
            status=SupplierStatus.ACTIVE,
        )

        assert supplier.id is not None
        fetched = await crud.get_supplier(supplier.id)
        assert fetched is not None
        assert fetched.name == "Release Supplier"

        items = await crud.list_suppliers(limit=10)
        assert any(item.id == supplier.id for item in items)

    await engine.dispose()


def test_supplier_business_smoke():
    asyncio.run(_supplier_smoke())
