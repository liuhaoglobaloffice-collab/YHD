"""
LiuHao AI OS Y1.0
Phase 5 — Task Test Fixtures
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.tasks.service import TaskService


@pytest_asyncio.fixture
async def task_service(async_session: AsyncSession) -> TaskService:
    """Create task service with real database session"""
    rbac = RBACService(async_session)
    return TaskService(
        session=async_session,
        rbac_service=rbac,
        audit_service=AuditService,
    )
