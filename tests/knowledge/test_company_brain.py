"""
CompanyBrain Tests

Covers:
- Entity create / persist / read
- Fact create / persist / read
- Fact conflict handling (priority-based)
- Entity list with type filter
- Permission checks
- Validation
"""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.knowledge.company_brain import (
    CompanyBrain,
    EntityType,
    FactConfidence,
    FactPriority,
)


class MockAudit(AuditService):
    """Audit stub that swallows log calls."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        pass


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user(is_superuser=True):
    """Create a test user."""
    user = User()
    user.id = 1
    user.username = "test_user"
    user.is_active = True
    user.is_superuser = is_superuser
    return user


def create_user_no_permission():
    """Create a user without KNOWLEDGE_WRITE permission."""
    user = User()
    user.id = 99
    user.username = "no_perm_user"
    user.is_active = True
    user.is_superuser = False
    return user


# ============================================================================
# Test 1: Entity create and persist
# ============================================================================


def test_create_entity_persists_to_database():
    """Test create_entity() creates an entity and persists to database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user,
                entity_type=EntityType.COMPANY,
                name="Acme Corp",
                attributes={"industry": "technology"},
            )

            assert entity is not None
            assert entity.name == "Acme Corp"
            assert entity.entity_type == EntityType.COMPANY
            assert entity.attributes == {"industry": "technology"}

    asyncio.run(_run())


def test_get_entity_returns_created_entity():
    """Test get_entity() returns the entity by ID."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            created = await brain.create_entity(
                user=user, entity_type=EntityType.PRODUCT, name="Widget",
            )

            fetched = await brain.get_entity(user=user, entity_id=created.id)
            assert fetched is not None
            assert fetched.id == created.id
            assert fetched.name == "Widget"

    asyncio.run(_run())


def test_get_entity_raises_not_found():
    """Test get_entity() raises NotFoundError for non-existent entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.get_entity(user=user, entity_id=str(uuid4()))

    asyncio.run(_run())


# ============================================================================
# Test 2: Entity list
# ============================================================================


def test_list_entities_returns_all():
    """Test list_entities() returns all entities."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await brain.create_entity(user=user, entity_type=EntityType.COMPANY, name="A")
            await brain.create_entity(user=user, entity_type=EntityType.PRODUCT, name="B")

            entities = await brain.list_entities(user=user)
            assert len(entities) == 2

    asyncio.run(_run())


def test_list_entities_filters_by_type():
    """Test list_entities() filters by entity type."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await brain.create_entity(user=user, entity_type=EntityType.COMPANY, name="Corp")
            await brain.create_entity(user=user, entity_type=EntityType.PRODUCT, name="Prod")

            companies = await brain.list_entities(user=user, entity_type=EntityType.COMPANY)
            assert len(companies) == 1
            assert companies[0].entity_type == EntityType.COMPANY

    asyncio.run(_run())


# ============================================================================
# Test 3: Fact create and persist
# ============================================================================


def test_create_fact_persists_to_database():
    """Test create_fact() creates a fact and persists to database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            fact = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="founded", value="2010",
                source="public_record", confidence=FactConfidence.VERIFIED,
                priority=FactPriority.VERIFIED,
            )

            assert fact is not None
            assert fact.attribute == "founded"
            assert fact.value == "2010"
            assert fact.is_active is True

    asyncio.run(_run())


def test_get_entity_facts_returns_facts():
    """Test get_entity_facts() returns facts for an entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Jane",
                source="public", confidence=FactConfidence.VERIFIED, priority=FactPriority.VERIFIED,
            )

            facts = await brain.get_entity_facts(user=user, entity_id=entity.id)
            assert len(facts) == 1
            assert facts[0].attribute == "ceo"

    asyncio.run(_run())


# ============================================================================
# Test 4: Fact conflict handling
# ============================================================================


def test_higher_priority_fact_supersedes_lower():
    """Test higher priority fact supersedes existing lower priority fact."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            # Create low priority fact
            fact1 = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Old CEO",
                source="internal", confidence=FactConfidence.LOW, priority=FactPriority.UNVERIFIED,
            )

            # Create higher priority fact - should supersede fact1
            fact2 = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="New CEO",
                source="official", confidence=FactConfidence.VERIFIED, priority=FactPriority.APPROVED,
            )

            # fact1 should now be inactive (superseded)
            facts = await brain.get_entity_facts(user=user, entity_id=entity.id, include_inactive=True)
            assert len(facts) == 2

            # Active fact should be the higher priority one
            active_facts = await brain.get_entity_facts(user=user, entity_id=entity.id)
            assert len(active_facts) == 1
            assert active_facts[0].value == "New CEO"

    asyncio.run(_run())


def test_lower_priority_fact_rejected():
    """Test lower priority fact is rejected when higher priority fact exists."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            # Create high priority fact first
            await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Real CEO",
                source="official", confidence=FactConfidence.VERIFIED, priority=FactPriority.OFFICIAL,
            )

            from src.core.errors import ValidationError

            # Try to create lower priority fact - should be rejected
            with pytest.raises(ValidationError):
                await brain.create_fact(
                    user=user, entity_id=entity.id, attribute="ceo", value="Fake CEO",
                    source="rumor", confidence=FactConfidence.LOW, priority=FactPriority.INFERRED,
                )

    asyncio.run(_run())


# ============================================================================
# Test 5: Permission checks
# ============================================================================


def test_create_entity_rejects_user_without_write_permission():
    """Test create_entity() raises PermissionDeniedError."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await brain.create_entity(
                    user=user, entity_type=EntityType.COMPANY, name="Test",
                )

    asyncio.run(_run())


# ============================================================================
# Test 6: Validation
# ============================================================================


def test_create_entity_rejects_empty_name():
    """Test create_entity() raises ValidationError for empty name."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import ValidationError

            with pytest.raises(ValidationError):
                await brain.create_entity(
                    user=user, entity_type=EntityType.COMPANY, name="   ",
                )

    asyncio.run(_run())


def test_create_fact_rejects_empty_attribute():
    """Test create_fact() raises ValidationError for empty attribute."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            from src.core.errors import ValidationError

            with pytest.raises(ValidationError):
                await brain.create_fact(
                    user=user, entity_id=entity.id, attribute="   ", value="x",
                    source="test", priority=FactPriority.UNVERIFIED,
                )

    asyncio.run(_run())


# ============================================================================
# Test 7: Entity update
# ============================================================================


def test_update_entity_updates_name():
    """Test update_entity() updates entity name."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Old Name",
            )

            updated = await brain.update_entity(
                user=user, entity_id=entity.id, name="New Name",
            )

            assert updated.name == "New Name"
            assert updated.id == entity.id

            # Verify persistence by re-fetching
            fetched = await brain.get_entity(user=user, entity_id=entity.id)
            assert fetched.name == "New Name"

    asyncio.run(_run())


def test_update_entity_updates_attributes():
    """Test update_entity() updates entity attributes."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
                attributes={"industry": "tech"},
            )

            updated = await brain.update_entity(
                user=user, entity_id=entity.id, attributes={"industry": "finance", "size": "large"},
            )

            assert updated.attributes == {"industry": "finance", "size": "large"}

    asyncio.run(_run())


def test_update_entity_rejects_empty_name():
    """Test update_entity() raises ValidationError for empty name."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            from src.core.errors import ValidationError

            with pytest.raises(ValidationError):
                await brain.update_entity(
                    user=user, entity_id=entity.id, name="   ",
                )

    asyncio.run(_run())


def test_update_entity_raises_not_found():
    """Test update_entity() raises NotFoundError for non-existent entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.update_entity(
                    user=user, entity_id=str(uuid4()), name="Test",
                )

    asyncio.run(_run())


def test_update_entity_no_changes_returns_existing():
    """Test update_entity() with no changes returns existing entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            updated = await brain.update_entity(user=user, entity_id=entity.id)
            assert updated.name == "Acme"
            assert updated.id == entity.id

    asyncio.run(_run())


def test_update_entity_rejects_user_without_write_permission():
    """Test update_entity() raises PermissionDeniedError."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await brain.update_entity(
                    user=user, entity_id=str(uuid4()), name="Test",
                )

    asyncio.run(_run())


# ============================================================================
# Test 8: Entity delete
# ============================================================================


def test_delete_entity_removes_entity():
    """Test delete_entity() removes entity from database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            deleted = await brain.delete_entity(user=user, entity_id=entity.id)
            assert deleted is True

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.get_entity(user=user, entity_id=entity.id)

    asyncio.run(_run())


def test_delete_entity_raises_not_found():
    """Test delete_entity() raises NotFoundError for non-existent entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.delete_entity(user=user, entity_id=str(uuid4()))

    asyncio.run(_run())


def test_delete_entity_rejects_user_without_write_permission():
    """Test delete_entity() raises PermissionDeniedError."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await brain.delete_entity(
                    user=user, entity_id=str(uuid4()),
                )

    asyncio.run(_run())


# ============================================================================
# Test 9: Fact update
# ============================================================================


def test_update_fact_updates_value():
    """Test update_fact() updates fact value."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            fact = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Jane",
                source="public", confidence=FactConfidence.VERIFIED,
                priority=FactPriority.VERIFIED,
            )

            updated = await brain.update_fact(
                user=user, fact_id=fact.id, value="John",
            )

            assert updated.value == "John"
            assert updated.id == fact.id

            # Verify persistence
            fetched = await brain.get_fact(user=user, fact_id=fact.id)
            assert fetched.value == "John"

    asyncio.run(_run())


def test_update_fact_updates_confidence_and_priority():
    """Test update_fact() updates confidence and priority."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            fact = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Jane",
                source="public", confidence=FactConfidence.LOW,
                priority=FactPriority.UNVERIFIED,
            )

            updated = await brain.update_fact(
                user=user, fact_id=fact.id,
                confidence=FactConfidence.VERIFIED,
                priority=FactPriority.OFFICIAL,
            )

            assert updated.confidence == FactConfidence.VERIFIED
            assert updated.priority == FactPriority.OFFICIAL

    asyncio.run(_run())


def test_update_fact_deactivates():
    """Test update_fact() can deactivate a fact."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            fact = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Jane",
                source="public", confidence=FactConfidence.VERIFIED,
                priority=FactPriority.VERIFIED,
            )

            updated = await brain.update_fact(
                user=user, fact_id=fact.id, is_active=False,
            )

            assert updated.is_active is False

            # Should not appear in active-only query
            facts = await brain.get_entity_facts(user=user, entity_id=entity.id)
            assert len(facts) == 0

            # Should appear with include_inactive
            all_facts = await brain.get_entity_facts(
                user=user, entity_id=entity.id, include_inactive=True,
            )
            assert len(all_facts) == 1

    asyncio.run(_run())


def test_update_fact_raises_not_found():
    """Test update_fact() raises NotFoundError for non-existent fact."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.update_fact(
                    user=user, fact_id=str(uuid4()), value="test",
                )

    asyncio.run(_run())


def test_update_fact_rejects_user_without_write_permission():
    """Test update_fact() raises PermissionDeniedError."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await brain.update_fact(
                    user=user, fact_id=str(uuid4()), value="test",
                )

    asyncio.run(_run())


# ============================================================================
# Test 10: Fact delete
# ============================================================================


def test_delete_fact_removes_fact():
    """Test delete_fact() removes fact from database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            entity = await brain.create_entity(
                user=user, entity_type=EntityType.COMPANY, name="Acme",
            )

            fact = await brain.create_fact(
                user=user, entity_id=entity.id, attribute="ceo", value="Jane",
                source="public", confidence=FactConfidence.VERIFIED,
                priority=FactPriority.VERIFIED,
            )

            deleted = await brain.delete_fact(user=user, fact_id=fact.id)
            assert deleted is True

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.get_fact(user=user, fact_id=fact.id)

    asyncio.run(_run())


def test_delete_fact_raises_not_found():
    """Test delete_fact() raises NotFoundError for non-existent fact."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.delete_fact(user=user, fact_id=str(uuid4()))

    asyncio.run(_run())


def test_delete_fact_rejects_user_without_write_permission():
    """Test delete_fact() raises PermissionDeniedError."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await brain.delete_fact(
                    user=user, fact_id=str(uuid4()),
                )

    asyncio.run(_run())


def test_create_fact_rejects_nonexistent_entity():
    """Test create_fact() raises NotFoundError for non-existent entity."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            brain = CompanyBrain(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import NotFoundError

            with pytest.raises(NotFoundError):
                await brain.create_fact(
                    user=user, entity_id=str(uuid4()), attribute="attr", value="val",
                    source="test", priority=FactPriority.UNVERIFIED,
                )

    asyncio.run(_run())