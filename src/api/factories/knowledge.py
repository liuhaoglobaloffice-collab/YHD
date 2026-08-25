"""
Knowledge Service Factory

Phase 4 Module 1: Dependency injection factory for Knowledge services.

Handles:
- DocumentService instantiation
- MemoryService instantiation
- CompanyBrain instantiation
- RBACService creation
- Aud itService integration
- PolicyEngine integration
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.knowledge.company_brain import CompanyBrain
from src.knowledge.documents import DocumentService
from src.knowledge.knowledge_retrieval import KnowledgeRetrievalService
from src.knowledge.memory import MemoryService
from src.security.policy import PolicyEngine


async def get_document_service(
    session: AsyncSession = Depends(get_db),
) -> DocumentService:
    """
    Create DocumentService with all dependencies.

    Phase 4 Module 1: Database Integration

    Dependencies injected:
    - AsyncSession (from database)
    - RBACService(session)
    - PolicyEngine()
    - AuditService (static class)

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured DocumentService instance
    """
    rbac_service = RBACService(session)
    policy_engine = PolicyEngine()

    return DocumentService(
        session=session,
        rbac_service=rbac_service,
        policy_engine=policy_engine,
        audit_service=AuditService,
    )


async def get_memory_service(
    session: AsyncSession = Depends(get_db),
) -> MemoryService:
    """
    Create MemoryService with all dependencies.

    Phase 4 Module 1: Database Integration

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured MemoryService instance
    """
    rbac_service = RBACService(session)

    return MemoryService(
        session=session,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )


async def get_company_brain(
    session: AsyncSession = Depends(get_db),
) -> CompanyBrain:
    """
    Create CompanyBrain with all dependencies.

    Phase 4 Module 1: Database Integration

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured CompanyBrain instance
    """
    rbac_service = RBACService(session)

    return CompanyBrain(
        session=session,
        rbac_service=rbac_service,
        audit_service=AuditService,
        company_id="default-company",
    )


async def get_knowledge_retrieval(
    session: AsyncSession = Depends(get_db),
) -> KnowledgeRetrievalService:
    """
    Create KnowledgeRetrievalService with all dependencies.

    Phase 4 Module 2: Knowledge Retrieval System

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured KnowledgeRetrievalService instance
    """
    rbac_service = RBACService(session)

    return KnowledgeRetrievalService(
        session=session,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )
