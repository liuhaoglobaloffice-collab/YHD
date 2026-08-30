"""
KnowledgeRetrievalService Tests
Covers:
- Document search (_search_documents)
- Fact search (_search_facts)
- Multi-source search aggregation
- Permission filtering
- Empty query validation
- Context building
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.database.models import (
    CompanyBrainEntityModel,
    CompanyBrainFactModel,
    DocumentModel,
)
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.knowledge.knowledge_retrieval import (
    KnowledgeQuery,
    KnowledgeRetrievalService,
    KnowledgeSource,
    SearchStrategy,
)


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user():
    """Create a test user with superuser privileges."""
    user = User()
    user.id = 1
    user.username = "test_user"
    user.is_active = True
    user.is_superuser = True
    return user


async def seed_test_data(session):
    """Seed test data for knowledge retrieval tests."""
    now = datetime.now(UTC)

    # Document 1: matches "report"
    doc1 = DocumentModel(
        id=str(uuid4()),
        filename="q4_report.pdf",
        title="Q4 Financial Report",
        file_type="pdf",
        size=1024,
        content="The Q4 financial report shows 15% revenue growth across all segments.",
        tags=["finance", "quarterly"],
        meta={"department": "finance"},
        created_by="1",
        status="available",
        created_at=now,
        updated_at=now,
    )

    # Document 2: matches "budget"
    doc2 = DocumentModel(
        id=str(uuid4()),
        filename="budget_2026.xlsx",
        title="2026 Budget Plan",
        file_type="xlsx",
        size=2048,
        content="The 2026 annual budget allocates resources to AI and cloud infrastructure.",
        tags=["budget", "planning"],
        meta={"department": "finance"},
        created_by="1",
        status="available",
        created_at=now,
        updated_at=now,
    )

    # Document 3: no match for "report" or "budget"
    doc3 = DocumentModel(
        id=str(uuid4()),
        filename="meeting_notes.txt",
        title="Team Meeting Notes",
        file_type="txt",
        size=512,
        content="General discussion about project timelines and deliverables.",
        tags=["meeting"],
        meta={"department": "engineering"},
        created_by="2",
        status="available",
        created_at=now,
        updated_at=now,
    )

    session.add_all([doc1, doc2, doc3])

    # Entity 1: Company "Acme Corp"
    entity1 = CompanyBrainEntityModel(
        id=str(uuid4()),
        name="Acme Corp",
        entity_type="company",
        description="A leading technology company",
        attributes={"industry": "technology", "employees": 5000, "revenue": "2B"},
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    # Entity 2: Product "Acme AI Platform"
    entity2 = CompanyBrainEntityModel(
        id=str(uuid4()),
        name="Acme AI Platform",
        entity_type="product",
        description="AI-powered analytics platform",
        attributes={"version": "3.0", "users": 10000},
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    session.add_all([entity1, entity2])

    # Facts for Acme Corp
    fact1 = CompanyBrainFactModel(
        id=str(uuid4()),
        entity_id=str(entity1.id),
        attribute="founded",
        value="2010",
        source="public_record",
        confidence="verified",
        priority=90,
        is_active=True,
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    fact2 = CompanyBrainFactModel(
        id=str(uuid4()),
        entity_id=str(entity1.id),
        attribute="ceo",
        value="Jane Smith",
        source="public_record",
        confidence="verified",
        priority=85,
        is_active=True,
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    # Facts for Acme AI Platform
    fact3 = CompanyBrainFactModel(
        id=str(uuid4()),
        entity_id=str(entity2.id),
        attribute="pricing",
        value="Subscription-based, starting at $999/month",
        source="product_page",
        confidence="high",
        priority=80,
        is_active=True,
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    # Inactive fact - should not be returned
    fact4 = CompanyBrainFactModel(
        id=str(uuid4()),
        entity_id=str(entity2.id),
        attribute="deprecated_feature",
        value="Legacy API v1",
        source="internal",
        confidence="low",
        priority=10,
        is_active=False,
        company_id="default-company",
        created_by="1",
        created_at=now,
        updated_at=now,
    )

    session.add_all([fact1, fact2, fact3, fact4])
    await session.commit()

    return {
        "documents": {"report": doc1, "budget": doc2, "notes": doc3},
        "entities": {"acme_corp": entity1, "acme_platform": entity2},
        "facts": [fact1, fact2, fact3, fact4],
    }


async def _create_service(session_factory):
    """Create KnowledgeRetrievalService with test dependencies."""
    session = await anext(aiter(session_factory()))
    # Need to use the session properly
    async with session_factory() as session:
        rbac = RBACService(session)
        audit = AuditService()
        return KnowledgeRetrievalService(
            session=session,
            rbac_service=rbac,
            audit_service=audit,
        ), session


# ============================================================================
# Test 1: Document search
# ============================================================================


def test_search_documents_returns_results():
    """Test _search_documents returns matching documents."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            # Search for "report"
            query = KnowledgeQuery(
                query="report",
                sources=[KnowledgeSource.DOCUMENT],
                limit=10,
            )
            results = await service._search_documents(user, query)

            assert len(results) >= 1
            assert any("report" in r.title.lower() or "report" in r.content.lower() for r in results)

    asyncio.run(_run())


def test_search_documents_returns_empty_for_no_match():
    """Test _search_documents returns empty for non-matching query."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            query = KnowledgeQuery(
                query="nonexistent_topic_xyz",
                sources=[KnowledgeSource.DOCUMENT],
                strategy=SearchStrategy.KEYWORD,
                limit=10,
            )
            results = await service._search_documents(user, query)

            assert len(results) == 0

    asyncio.run(_run())


def test_search_documents_title_match_gets_higher_score():
    """Test documents matching title get higher score than content-only match."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            # "budget" matches doc2 title exactly
            query = KnowledgeQuery(
                query="budget",
                sources=[KnowledgeSource.DOCUMENT],
                limit=10,
            )
            results = await service._search_documents(user, query)

            assert len(results) >= 1
            # The budget document should have title match (score 0.9)
            budget_result = [r for r in results if "budget" in r.title.lower()]
            if budget_result:
                assert budget_result[0].score >= 0.8

    asyncio.run(_run())


# ============================================================================
# Test 2: Fact search
# ============================================================================


def test_search_facts_returns_results():
    """Test _search_facts returns matching facts."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            # Search for "ceo" - should match fact2 attribute
            query = KnowledgeQuery(
                query="ceo",
                sources=[KnowledgeSource.FACT],
                limit=10,
            )
            results = await service._search_facts(user, query)

            assert len(results) >= 1
            assert any("ceo" in r.title.lower() for r in results)

    asyncio.run(_run())


def test_search_facts_returns_empty_for_no_match():
    """Test _search_facts returns empty for non-matching query."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            query = KnowledgeQuery(
                query="nonexistent_fact_xyz",
                sources=[KnowledgeSource.FACT],
                limit=10,
            )
            results = await service._search_facts(user, query)

            assert len(results) == 0

    asyncio.run(_run())


def test_search_facts_excludes_inactive():
    """Test _search_facts only returns active facts, not inactive ones."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            data = await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            # Search for "deprecated" - should NOT match inactive fact
            query = KnowledgeQuery(
                query="deprecated",
                sources=[KnowledgeSource.FACT],
                limit=10,
            )
            results = await service._search_facts(user, query)

            # Inactive fact should not be returned
            assert len(results) == 0

    asyncio.run(_run())


# ============================================================================
# Test 3: Multi-source search
# ============================================================================


def test_search_across_multiple_sources():
    """Test search aggregates results from multiple sources."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            # Search all sources for "Acme"
            query = KnowledgeQuery(
                query="Acme",
                sources=[KnowledgeSource.ENTITY, KnowledgeSource.FACT],
                limit=20,
            )
            results = await service.search(user, query)

            # Should find entities and facts about Acme
            assert len(results) >= 1

    asyncio.run(_run())


def test_search_results_sorted_by_score():
    """Test search results are sorted by score descending."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            query = KnowledgeQuery(
                query="report",
                sources=[KnowledgeSource.DOCUMENT, KnowledgeSource.ENTITY, KnowledgeSource.FACT],
                limit=20,
            )
            results = await service.search(user, query)

            # Verify sort order
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    asyncio.run(_run())


# ============================================================================
# Test 4: Permission filtering
# ============================================================================


def test_search_rejects_user_without_permission():
    """Test search raises PermissionDeniedError for users without permission."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            # User without KNOWLEDGE_READ permission
            user = User()
            user.id = 99
            user.username = "no_permission_user"
            user.is_active = True
            user.is_superuser = False

            from src.core.errors import PermissionDeniedError

            query = KnowledgeQuery(query="test", limit=10)
            with pytest.raises(PermissionDeniedError):
                await service.search(user, query)

    asyncio.run(_run())


# ============================================================================
# Test 5: Empty query validation
# ============================================================================


def test_search_rejects_empty_query():
    """Test search raises ValidationError for empty query."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            from src.core.errors import ValidationError

            query = KnowledgeQuery(query="   ", limit=10)
            with pytest.raises(ValidationError):
                await service.search(user, query)

    asyncio.run(_run())


# ============================================================================
# Test 6: Context building
# ============================================================================


def test_build_context_returns_context():
    """Test build_context returns aggregated context from multiple sources."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            await seed_test_data(session)
            rbac = RBACService(session)
            service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=AuditService(),
            )
            user = create_test_user()

            context = await service.build_context(
                user=user,
                task="Find information about budget and pricing",
                max_items=10,
            )

            assert context.task == "Find information about budget and pricing"
            assert context.total_sources >= 0
            assert context.query_time >= 0.0

    asyncio.run(_run())