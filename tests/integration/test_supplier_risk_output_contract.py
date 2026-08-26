import asyncio
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.models import Supplier, SupplierRiskAssessment, RiskLevel


async def _create_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def _assert_contract(result):
    # required keys
    keys = [
        "supplier_id",
        "assessment_id",
        "risk_level",
        "risk_score",
        "overall_score",
        "risk_factors",
        "recommendations",
    ]
    for k in keys:
        assert k in result, f"Missing key {k} in result"

    assert isinstance(result["supplier_id"], int)
    assert (isinstance(result["assessment_id"], int) or result["assessment_id"] is None)
    assert isinstance(result["risk_level"], str)
    assert isinstance(result["risk_score"], float)
    assert isinstance(result["overall_score"], float)
    assert isinstance(result["risk_factors"], dict)
    assert isinstance(result["recommendations"], list)
    for item in result["recommendations"]:
        assert isinstance(item, str)


def test_assess_risk_normal_ai_json():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            # create supplier
            supplier = Supplier(name="S-Normal", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            # normal AI JSON
            ai_payload = json.dumps({
                "compliance_score": 90,
                "financial_score": 85,
                "delivery_score": 80,
                "quality_score": 75,
                "communication_score": 70,
                "overall_score": 80,
                "risk_level": "LOW",
                "strengths": ["s1"],
                "weaknesses": ["w1"],
                "opportunities": ["o1"],
                "threats": ["t1"],
                "recommendations": ["rec1", "rec2"],
            }, ensure_ascii=False)

            async def fake_ai(prompt):
                return ai_payload

            agent._call_ai_analysis = fake_ai

            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            _assert_contract(res)
            assert res["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    asyncio.run(_run())


def test_assess_risk_ai_empty_response_uses_default():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            supplier = Supplier(name="S-Empty", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            async def fake_ai(prompt):
                return ""  # empty

            agent._call_ai_analysis = fake_ai

            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            _assert_contract(res)
            # default risk_level should be MEDIUM
            assert res["risk_level"] == "MEDIUM"

    asyncio.run(_run())


def test_assess_risk_ai_malformed_json_uses_default():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            supplier = Supplier(name="S-BadJSON", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            async def fake_ai(prompt):
                return "{not a valid json}"

            agent._call_ai_analysis = fake_ai

            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            _assert_contract(res)
            assert res["risk_level"] == "MEDIUM"

    asyncio.run(_run())


def test_assess_risk_risk_level_unknown_defaults_to_medium():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            supplier = Supplier(name="S-Unknown", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            ai_payload = json.dumps({
                "compliance_score": 50,
                "financial_score": 50,
                "delivery_score": 50,
                "quality_score": 50,
                "communication_score": 50,
                "overall_score": 50,
                "risk_level": "UNKNOWN_LEVEL",
                "recommendations": ["rec"],
            })

            async def fake_ai(prompt):
                return ai_payload

            agent._call_ai_analysis = fake_ai

            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            _assert_contract(res)
            # unknown mapped to MEDIUM
            assert res["risk_level"] == "MEDIUM"

    asyncio.run(_run())


def test_assess_risk_scores_as_strings_are_normalized():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            supplier = Supplier(name="S-Strings", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            ai_payload = json.dumps({
                "compliance_score": "90",
                "financial_score": "85.5",
                "delivery_score": "80",
                "quality_score": "75",
                "communication_score": "70",
                "overall_score": "82",
                "risk_level": "LOW",
                "recommendations": ["rec1"],
            })

            async def fake_ai(prompt):
                return ai_payload

            agent._call_ai_analysis = fake_ai

            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            _assert_contract(res)
            assert isinstance(res["overall_score"], float)
            assert isinstance(res["risk_score"], float)

    asyncio.run(_run())
