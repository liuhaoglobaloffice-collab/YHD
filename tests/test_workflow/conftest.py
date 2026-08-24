"""
LiuHao AI OS Y1.0
Phase 5 — Workflow Test Fixtures
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.workflow.service import WorkflowService


@pytest_asyncio.fixture
async def workflow_service(async_session: AsyncSession) -> WorkflowService:
    """Create workflow service with real database session"""
    rbac = RBACService(async_session)
    return WorkflowService(
        session=async_session,
        rbac_service=rbac,
        audit_service=AuditService,
    )
