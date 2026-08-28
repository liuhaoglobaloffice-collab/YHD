import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.business.supplier.task_adapter import build_task_payload_from_assessment
from src.tasks.service import TaskService
from src.identity.audit import AuditAction
from src.identity.models import AuditLog
from src.business.supplier.models import Supplier, SupplierRiskAssessment, RiskLevel


async def _create_test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_create_task_from_assessment_creates_task_and_audit():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            # prepare supplier
            supplier = Supplier(name="S-Task", country="CN", product_category="X", business_type="trading", status="active")
            session.add(supplier)
            await session.commit()
            await session.refresh(supplier)

            # create an assessment record
            assessment = SupplierRiskAssessment(
                supplier_id=supplier.id,
                compliance_score=50.0,
                financial_score=50.0,
                delivery_score=50.0,
                quality_score=50.0,
                communication_score=50.0,
                overall_score=50.0,
                risk_level=RiskLevel.MEDIUM,
                strengths=json.dumps(["s"]),
                weaknesses=json.dumps(["w"]),
                opportunities=json.dumps(["o"]),
                threats=json.dumps(["t"]),
                recommendations=json.dumps(["rec"]),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(assessment)
            await session.commit()
            await session.refresh(assessment)

            # build payload
            assessment_dict = {
                "supplier_id": supplier.id,
                "assessment_id": assessment.id,
                "risk_level": "HIGH",
                "overall_score": 30.0,
                "risk_score": 70.0,
                "risk_factors": {"financial_score": 30},
                "recommendations": ["Review immediately"],
            }

            payload = build_task_payload_from_assessment(assessment_dict, created_by="tester")

            service = TaskService(session)
            task = await service.create_task_from_assessment(assessment_dict, actor=None)

            # Assert task exists in DB
            from src.database.models import TaskModel

            res = await session.execute(select(TaskModel).where(TaskModel.id == str(task.id)))
            tm = res.scalar_one_or_none()
            assert tm is not None
            assert tm.title is not None
            meta = tm.meta or {}
            assert isinstance(meta, dict) or isinstance(meta, (str,))
            # if stored as JSON, ensure assessment_reference present
            if isinstance(meta, dict):
                assert meta.get("assessment_reference", {}).get("assessment_id") == assessment.id

            # Assert audit log created
            res2 = await session.execute(select(AuditLog).where(AuditLog.resource_type == "task", AuditLog.resource_id == str(task.id)))
            audit_rec = res2.scalars().first()
            assert audit_rec is not None
            assert audit_rec.action in (AuditAction.TASK_CREATED.value, AuditAction.CREATE.value, "task_created")

    asyncio.run(_run())


def test_create_task_from_assessment_missing_assessment_id_raises():
    async def _run():
        session_factory = await _create_test_session()
        async with session_factory() as session:
            service = TaskService(session)
            try:
                await service.create_task_from_assessment({"supplier_id": 5}, actor=None)
                raise AssertionError("Expected ValueError")
            except ValueError:
                pass

    asyncio.run(_run())
