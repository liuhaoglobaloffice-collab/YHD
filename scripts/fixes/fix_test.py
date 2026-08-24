"""Script to fix test_knowledge_retrieval.py"""

test_content = '''"""
LiuHao AI OS Y1.0
Phase 4 Module 2 — Knowledge Retrieval System Tests

Tests for unified knowledge retrieval service.
"""

import pytest
from datetime import datetime, UTC

from src.knowledge.knowledge_retrieval import (
    KnowledgeRetrievalService,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeContext,
    KnowledgeSource,
    SearchStrategy,
)
from src.core.errors import PermissionDeniedError, ValidationError
from src.identity.models import User, RoleEnum
from src.identity.rbac import RBACService, Permission
from src.identity.audit import AuditService, AuditAction
from src.database.repositories.knowledge import (
    MemoryRepository,
    CompanyBrainEntityRepository,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def retrieval_service(async_session, rbac_service):
    """Knowledge retrieval service fixture"""
    return KnowledgeRetrievalService(
        session=async_session,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )


@pytest.fixture
async def test_memories(async_session, admin_user):
    """Create test memories using admin_user from conftest"""
    memory_repo = MemoryRepository(async_session)
    
    memories = [
        await memory_repo.create(
            user_id=admin_user.id,
            memory_type="product",
            content='{"key": "food packaging", "value": "High quality plastic food containers"}',
            importance=5,
        ),
        await memory_repo.create(
            user_id=admin_user.id,
            memory_type="market",
            content='{"key": "southeast asia", "value": "Growing demand for packaging solutions"}',
            importance=4,
        ),
    ]
    await async_session.commit()
    return memories


@pytest.fixture
async def test_entities(async_session):
    """Create test company entities"""
    entity_repo = CompanyBrainEntityRepository(async_session)
    
    entities = [
        await entity_repo.create(
            entity_type="product",
            name="Food Packaging Container",
            data={"material": "plastic", "capacity": "500ml"},
        ),
        await entity_repo.create(
            entity_type="market",
            name="Southeast Asia Market",
            data={"region": "ASEAN", "growth_rate": "15%"},
        ),
    ]
    await async_session.commit()
    return entities


# ============================================================================
# Test: Query Model
# ============================================================================

async def test_knowledge_query_defaults():
    """Test KnowledgeQuery default values"""
    query = KnowledgeQuery(query="test")
    
    assert query.query == "test"
    assert query.sources == [KnowledgeSource.ALL]
    assert query.strategy == SearchStrategy.HYBRID
    assert query.limit == 10
    assert query.offset == 0


# ============================================================================
# Test: Search Functionality
# ============================================================================

async def test_search_memories(
    retrieval_service, admin_user, test_memories, async_session
):
    """Test searching memories"""
    query = KnowledgeQuery(
        query="packaging",
        sources=[KnowledgeSource.MEMORY],
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    assert len(results) > 0
    assert any("packaging" in r.content.lower() for r in results)
    assert all(r.source == KnowledgeSource.MEMORY for r in results)


async def test_search_entities(
    retrieval_service, admin_user, test_entities, async_session
):
    """Test searching company entities"""
    query = KnowledgeQuery(
        query="market",
        sources=[KnowledgeSource.ENTITY],
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    assert len(results) > 0
    assert any("market" in r.title.lower() for r in results)
    assert all(r.source == KnowledgeSource.ENTITY for r in results)


async def test_search_all_sources(
    retrieval_service, admin_user, test_memories, test_entities, async_session
):
    """Test searching across all sources"""
    query = KnowledgeQuery(
        query="asia",
        sources=[KnowledgeSource.ALL],
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    # Should find results from multiple sources
    assert len(results) > 0


async def test_search_with_pagination(
    retrieval_service, admin_user, test_memories, async_session
):
    """Test search with limit and offset"""
    query = KnowledgeQuery(
        query="packaging",
        sources=[KnowledgeSource.MEMORY],
        limit=1,
        offset=0,
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    assert len(results) <= 1


async def test_search_empty_query_fails(retrieval_service, admin_user):
    """Test that empty query raises validation error"""
    query = KnowledgeQuery(query="")
    
    with pytest.raises(ValidationError):
        await retrieval_service.search(admin_user, query)


async def test_search_without_permission_fails(retrieval_service, regular_user):
    """Test search fails without KNOWLEDGE_READ permission"""
    query = KnowledgeQuery(query="test")
    
    # regular_user does not have KNOWLEDGE_READ permission by default
    with pytest.raises(PermissionDeniedError):
        await retrieval_service.search(regular_user, query)


# ============================================================================
# Test: Context Building
# ============================================================================

async def test_build_context(
    retrieval_service, admin_user, test_memories, test_entities, async_session
):
    """Test building knowledge context for AI Brain"""
    context = await retrieval_service.build_context(
        user=admin_user,
        task="Analyze Southeast Asia food packaging market",
        max_items=5,
    )
    
    assert isinstance(context, KnowledgeContext)
    assert context.task == "Analyze Southeast Asia food packaging market"
    assert context.total_sources > 0
    assert context.query_time > 0
    assert len(context.results) > 0


async def test_context_summary(retrieval_service, admin_user, test_memories):
    """Test context summary generation"""
    context = await retrieval_service.build_context(
        user=admin_user,
        task="Test task",
        max_items=5,
    )
    
    summary = context.get_summary()
    
    assert isinstance(summary, str)
    assert "Test task" in summary
    assert "source" in summary.lower()


async def test_context_to_dict(retrieval_service, admin_user, test_memories):
    """Test context serialization"""
    context = await retrieval_service.build_context(
        user=admin_user,
        task="Test task",
        max_items=5,
    )
    
    data = context.to_dict()
    
    assert "task" in data
    assert "results" in data
    assert "total_sources" in data
    assert "query_time" in data


# ============================================================================
# Test: Data Models
# ============================================================================

async def test_knowledge_result_to_dict():
    """Test KnowledgeResult serialization"""
    result = KnowledgeResult(
        source=KnowledgeSource.MEMORY,
        title="Test Memory",
        content="Test content",
        relevance=0.9,
        metadata={"key": "value"},
    )
    
    data = result.to_dict()
    
    assert data["source"] == "memory"
    assert data["title"] == "Test Memory"
    assert data["content"] == "Test content"
    assert data["relevance"] == 0.9
    assert data["metadata"] == {"key": "value"}


# ============================================================================
# Test: Advanced Filtering
# ============================================================================

async def test_search_with_entity_type_filter(
    retrieval_service, admin_user, test_entities, async_session
):
    """Test searching with entity type filter"""
    query = KnowledgeQuery(
        query="market",
        sources=[KnowledgeSource.ENTITY],
        entity_type="market",
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    assert all(r.source == KnowledgeSource.ENTITY for r in results)


async def test_search_with_memory_type_filter(
    retrieval_service, admin_user, test_memories, async_session
):
    """Test searching with memory type filter"""
    query = KnowledgeQuery(
        query="packaging",
        sources=[KnowledgeSource.MEMORY],
        memory_type="product",
    )
    
    results = await retrieval_service.search(admin_user, query)
    
    assert all(r.source == KnowledgeSource.MEMORY for r in results)


# ============================================================================
# Test: Audit Integration
# ============================================================================

async def test_search_creates_audit_log(
    retrieval_service, admin_user, test_memories, async_session
):
    """Test that search creates audit log"""
    query = KnowledgeQuery(query="packaging")
    
    await retrieval_service.search(admin_user, query)
    
    # Check audit log was created
    from src.database.models import AuditLog
    from sqlalchemy import select
    
    result = await async_session.execute(
        select(AuditLog)
        .where(AuditLog.action == AuditAction.KNOWLEDGE_SEARCH.value)
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    
    assert audit is not None
    assert audit.user_id == admin_user.id


async def test_context_build_creates_audit_log(
    retrieval_service, admin_user, test_memories, async_session
):
    """Test that context building creates audit log"""
    await retrieval_service.build_context(
        user=admin_user,
        task="Test task",
        max_items=5,
    )
    
    # Check audit log was created
    from src.database.models import AuditLog
    from sqlalchemy import select
    
    result = await async_session.execute(
        select(AuditLog)
        .where(AuditLog.action == AuditAction.KNOWLEDGE_CONTEXT_BUILD.value)
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    
    assert audit is not None
    assert audit.user_id == admin_user.id


# ============================================================================
# Test: Complete Workflow
# ============================================================================

async def test_full_knowledge_retrieval_workflow(
    retrieval_service, admin_user, test_memories, test_entities, async_session
):
    """Test complete knowledge retrieval workflow"""
    # 1. Search for knowledge
    search_query = KnowledgeQuery(
        query="packaging",
        sources=[KnowledgeSource.ALL],
    )
    search_results = await retrieval_service.search(admin_user, search_query)
    
    assert len(search_results) > 0
    
    # 2. Build context for AI Brain
    context = await retrieval_service.build_context(
        user=admin_user,
        task="Develop Southeast Asia food packaging market",
        max_items=10,
    )
    
    assert context.total_sources > 0
    assert len(context.results) > 0
    
    # 3. Verify context is usable
    summary = context.get_summary()
    assert "Develop Southeast Asia food packaging market" in summary
'''

# Write the fixed test file
with open('tests/test_knowledge/test_knowledge_retrieval.py', 'w', encoding='utf-8') as f:
    f.write(test_content)

print("✅ Test file successfully updated with admin_user fixture")
print("✅ Fixed UUID binding issue by using conftest fixtures")
