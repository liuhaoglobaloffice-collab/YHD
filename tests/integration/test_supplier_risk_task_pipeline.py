import asyncio
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.models import Supplier, SupplierRiskAssessment, RiskLevel
from src.tasks.service import TaskService
from src.identity.models import AuditLog
from src.database.models import TaskModel
from src.identity.audit import AuditAction


async def _create_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_high_risk_generates_task_and_audit():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            # prepare supplier
            supplier = Supplier(name="S-Pipeline", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            # AI returns HIGH risk
            ai_payload = json.dumps({
                "compliance_score": 30,
                "financial_score": 30,
                "delivery_score": 30,
                "quality_score": 30,
                "communication_score": 30,
                "overall_score": 30,
                "risk_level": "HIGH",
                "recommendations": ["Immediate review"],
            })

            async def fake_ai(prompt):
                return ai_payload

            agent._call_ai_analysis = fake_ai

            # run assessment and persist
            assessment_result = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            # Ensure assessment_id present
            assert assessment_result["assessment_id"] is not None

            # create task from assessment
            service = TaskService(session)
            task = await service.create_task_from_assessment(assessment_result, actor=None)

            # verify task persisted
            res = await session.execute(select(TaskModel).where(TaskModel.id == str(task.id)))
            tm = res.scalar_one_or_none()
            assert tm is not None

            # verify meta contains assessment_reference
            meta = tm.meta or {}
            assert isinstance(meta, dict)
            assert meta.get("assessment_reference", {}).get("assessment_id") == assessment_result["assessment_id"]

            # verify audit log was created
            res2 = await session.execute(select(AuditLog).where(AuditLog.resource_type == "task", AuditLog.resource_id == str(task.id)))
            audit = res2.scalars().first()
            assert audit is not None
            assert audit.action in (AuditAction.TASK_CREATED.value, AuditAction.CREATE.value, "task_created")

    asyncio.run(_run())


def test_create_task_rejects_missing_assessment_id():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            service = TaskService(session)
            try:
                await service.create_task_from_assessment({"supplier_id": 1}, actor=None)
                raise AssertionError("Expected ValueError")
            except ValueError:
                pass

    asyncio.run(_run())


def test_pipeline_edge_cases_handle_errors_gracefully():
    async def _run():
        sf = await _create_session_factory()
        async with sf() as session:
            supplier = Supplier(name="S-Edge", country="CN", product_category="P", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            agent = SupplierRiskAgent(session)

            # AI returns malformed response
            async def bad_ai(prompt):
                return "no json here"

            agent._call_ai_analysis = bad_ai
            res = await agent.assess_risk(supplier_id=supplier.id, save_to_db=True)
            # Should still produce assessment_id and default MEDIUM
            assert res["assessment_id"] is not None
            assert res["risk_level"] == "MEDIUM"

            # recommendations may be default list
            assert isinstance(res["recommendations"], list)

            # Now try to create task from this default assessment
            service = TaskService(session)
            task = await service.create_task_from_assessment(res, actor=None)
            assert task is not None

    asyncio.run(_run())
