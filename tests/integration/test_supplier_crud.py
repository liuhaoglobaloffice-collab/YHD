import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import BusinessType, Supplier, SupplierStatus
from src.database.base import Base


async def _create_test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_supplier_crud_create_read_update_delete_flow():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            crud = SupplierCRUD(session)
            supplier = await crud.create_supplier(
                name="Acme Factory",
                country="CN",
                product_category="Electrical",
                business_type=BusinessType.MANUFACTURER,
                status=SupplierStatus.PENDING,
                industry="Manufacturing",
                email="sales@example.com",
                phone="12345678",
                website="https://example.com",
                description="Stock supplier",
            )
            assert supplier.id is not None
            fetched = await crud.get_supplier(supplier.id)
            assert fetched is not None
            assert fetched.name == "Acme Factory"

            updated = await crud.update_supplier(supplier.id, name="Acme Factory Updated")
            assert updated is not None
            assert updated.name == "Acme Factory Updated"

            deleted_ok = await crud.delete_supplier(supplier.id)
            assert deleted_ok is True
            soft_deleted = await crud.get_supplier(supplier.id)
            assert soft_deleted is None

    asyncio.run(_run())
