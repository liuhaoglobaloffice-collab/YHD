import asyncio
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.business.supplier.models import Supplier, SupplierRiskAssessment, RiskLevel
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.database.base import Base


async def _create_test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_assess_risk_handles_empty_ai_response():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            supplier = Supplier(name="S-EmptyAI", country="CN", product_category="X", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            # monkeypatch the AI call to return empty string
            async def _empty(prompt: str):
                return ""

            agent._call_ai_analysis = _empty

            result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)

            # Should fallback to default assessment
            assert result["overall_score"] == 50.0
            assert result["risk_level"] in ("MEDIUM", "medium",)
            assert result["assessment_id"] is not None

    asyncio.run(_run())


def test_assess_risk_handles_non_json_ai_response():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            supplier = Supplier(name="S-NonJSON", country="CN", product_category="X", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            async def _nonjson(prompt: str):
                return "I think this supplier is OK but here's no JSON"

            agent._call_ai_analysis = _nonjson

            result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            assert result["overall_score"] == 50.0
            assert isinstance(result["recommendations"], list)

    asyncio.run(_run())


def test_assess_risk_handles_json_missing_fields():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            supplier = Supplier(name="S-MissingFields", country="CN", product_category="X", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            async def _partial_json(prompt: str):
                return json.dumps({"compliance_score": 80.0})

            agent._call_ai_analysis = _partial_json

            result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            # Missing required fields should trigger fallback default
            assert result["overall_score"] == 50.0

    asyncio.run(_run())


def test_assess_risk_numeric_string_and_unknown_level_normalizes():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            supplier = Supplier(name="S-StringNums", country="CN", product_category="X", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            payload = {
                "compliance_score": "70",
                "financial_score": "65",
                "delivery_score": "60",
                "quality_score": "75",
                "communication_score": "80",
                "overall_score": "70",
                "risk_level": "UNKNOWN",
                "strengths": ["s1"],
                "weaknesses": ["w1"],
                "opportunities": ["o1"],
                "threats": ["t1"],
            }

            async def _weird_json(prompt: str):
                return json.dumps(payload)

            agent._call_ai_analysis = _weird_json

            result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)

            # overall_score normalized to float
            assert isinstance(result["overall_score"], float)
            assert result["overall_score"] == 70.0
            # unknown risk_level should default to MEDIUM
            assert result["risk_level"] in ("MEDIUM", "medium")

    asyncio.run(_run())


def test_history_distribution_and_high_risk_behaviors():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            # prepare two suppliers
            s1 = Supplier(name="S1", country="CN", product_category="X", business_type="manufacturer", status="active")
            s2 = Supplier(name="S2", country="CN", product_category="Y", business_type="trading", status="active")
            session.add_all([s1, s2])
            await session.commit()
            await session.refresh(s1)
            await session.refresh(s2)

            agent = SupplierRiskAgent(session)

            # Create assessments for s1: first MEDIUM then HIGH
            async def _first(prompt: str):
                return json.dumps({
                    "compliance_score": 80,
                    "financial_score": 80,
                    "delivery_score": 80,
                    "quality_score": 80,
                    "communication_score": 80,
                    "overall_score": 80,
                    "risk_level": "MEDIUM",
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                })

            async def _second_high(prompt: str):
                return json.dumps({
                    "compliance_score": 30,
                    "financial_score": 30,
                    "delivery_score": 30,
                    "quality_score": 30,
                    "communication_score": 30,
                    "overall_score": 30,
                    "risk_level": "HIGH",
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                })

            # s1 first
            agent._call_ai_analysis = _first
            r1 = await agent.assess_risk(supplier_id=s1.id, save_to_db=True)

            # s2 high
            agent._call_ai_analysis = _second_high
            r2 = await agent.assess_risk(supplier_id=s2.id, save_to_db=True)

            # s1 second (now high)
            agent._call_ai_analysis = _second_high
            r3 = await agent.assess_risk(supplier_id=s1.id, save_to_db=True)

            # history for s1 should have at least 2 entries, most recent first
            history = await agent.get_risk_history(supplier_id=s1.id, limit=5)
            assert len(history) >= 2
            assert history[0].created_at >= history[1].created_at

            # distribution: latest per supplier: s1->HIGH, s2->HIGH -> high count 2
            dist = await agent.get_risk_distribution()
            high_count = dist.get("HIGH", 0) + dist.get("CRITICAL", 0)
            assert high_count >= 2

            # get_high_risk_suppliers should dedupe and respect limit
            high_suppliers = await agent.get_high_risk_suppliers(limit=1)
            assert len(high_suppliers) == 1
            sup, ass = high_suppliers[0]
            assert sup.id in (s1.id, s2.id)

    asyncio.run(_run())
