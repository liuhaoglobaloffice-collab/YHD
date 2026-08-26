import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.routes.supplier import SupplierCreateRequest, create_supplier
from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import Supplier, SupplierRiskAssessment
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.database.base import Base
from src.identity.models import RoleEnum, User


async def _create_test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_supplier_create_accepts_iso_dates_and_returns_numeric_id():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            user = User(
                username="supplier-admin",
                email="supplier-admin@example.com",
                hashed_password="hashed",
                full_name="Supplier Admin",
                role=RoleEnum.ADMIN,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            request = SupplierCreateRequest(
                name="Alpha Manufacturing Ltd",
                business_type="manufacturer",
                country="CN",
                product_category="Industrial parts",
                email="sales@alpha.example",
                established_date="2024-01-15",
            )

            response = await create_supplier(
                request=request,
                session=session,
                current_user=user,
                _=None,
            )

            assert isinstance(response.id, int)
            assert response.id > 0
            assert response.established_date.startswith("2024-01-15")

            crud = SupplierCRUD(session)
            stored = await crud.get_supplier(response.id)
            assert stored is not None
            assert stored.established_date is not None
            assert stored.established_date.isoformat().startswith("2024-01-15")

    asyncio.run(_run())


def test_supplier_crud_normalizes_string_dates():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            crud = SupplierCRUD(session)
            supplier = await crud.create_supplier(
                name="Beta Trading Co",
                country="CN",
                product_category="Electronics",
                business_type="trading",
                established_date="2023-05-20",
            )

            assert supplier.id is not None
            assert supplier.established_date is not None
            assert supplier.established_date.isoformat().startswith("2023-05-20")

    asyncio.run(_run())


def test_supplier_risk_agent_returns_stable_contract():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            supplier = Supplier(
                name="Gamma Risk Ltd",
                country="CN",
                product_category="Industrial maintenance",
                business_type="manufacturer",
                status="active",
            )
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)
            result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)

            assert set(["supplier_id", "risk_level", "risk_score", "overall_score", "risk_factors", "recommendations", "assessment_id"]).issubset(result.keys())
            assert result["supplier_id"] == supplier.id
            assert isinstance(result["risk_factors"], dict)
            assert isinstance(result["recommendations"], list)
            assert result["assessment_id"] is not None

            stored = await session.execute(
                select(SupplierRiskAssessment).where(SupplierRiskAssessment.id == result["assessment_id"])
            )
            persisted = stored.scalar_one()
            assert persisted.supplier_id == supplier.id
            assert persisted.overall_score == result["overall_score"]

    asyncio.run(_run())


def test_supplier_risk_agent_handles_invalid_ai_payload():
    agent = SupplierRiskAgent.__new__(SupplierRiskAgent)
    payload = agent._parse_ai_response("not json at all")
    required = {"supplier_id", "risk_level", "risk_score", "overall_score", "risk_factors", "recommendations", "assessment_id"}
    assert set(required).issubset(set(agent._normalize_risk_result(7, payload, 99).keys()))
    assert payload["risk_level"].value == "medium"
