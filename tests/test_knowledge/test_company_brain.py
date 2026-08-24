"""
Tests for Company Brain
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.errors import ValidationError
from src.identity.models import RoleEnum, User
from src.identity.rbac import Permission
from src.knowledge.company_brain import (
    CompanyBrain,
    Entity,
    EntityType,
    Fact,
    FactConfidence,
    FactPriority,
)


@pytest.fixture
def regular_user():
    """Regular user fixture"""
    from uuid import uuid4

    return User(
        id=str(uuid4()),
        username="testuser",
        email="user@test.com",
        hashed_password="hashed",
        role=RoleEnum.USER,
        is_active=True,
    )


@pytest.fixture
def mock_rbac():
    """Mock RBAC service"""

    class MockRBAC:
        def has_permission(self, user, permission):
            if permission in [Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE]:
                return True
            return False

    return MockRBAC()


@pytest.fixture
def mock_audit():
    """Mock audit service"""

    class MockAudit:
        async def log(
            self,
            session,
            action,
            status,
            user_id=None,
            resource_type=None,
            resource_id=None,
            details=None,
            **kwargs,
        ):
            pass

        async def log_permission_denied(
            self, session, user_id, action, resource_type, reason, resource_id=None, **kwargs
        ):
            pass

    return MockAudit()


@pytest_asyncio.fixture
async def async_session():
    """Test database session"""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create tables
    from src.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def company_brain(async_session, mock_rbac, mock_audit):
    """Company brain fixture"""
    return CompanyBrain(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )


class TestEntity:
    """Test Entity"""

    def test_entity_creation(self):
        """Test entity creation"""
        entity = Entity(
            id="entity1",
            entity_type=EntityType.PRODUCT,
            name="Product A",
            attributes={"sku": "SKU001"},
        )

        assert entity.id == "entity1"
        assert entity.entity_type == EntityType.PRODUCT
        assert entity.name == "Product A"
        assert entity.attributes["sku"] == "SKU001"

    def test_entity_to_dict(self):
        """Test entity to_dict"""
        entity = Entity(
            id="entity1",
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )

        data = entity.to_dict()
        assert data["id"] == "entity1"
        assert data["entity_type"] == "product"
        assert data["name"] == "Product A"


class TestFact:
    """Test Fact"""

    def test_fact_creation(self):
        """Test fact creation"""
        fact = Fact(
            id="fact1",
            entity_id="entity1",
            attribute="price",
            value=100.0,
            source="document1",
            confidence=FactConfidence.VERIFIED,
            priority=FactPriority.OFFICIAL,
        )

        assert fact.id == "fact1"
        assert fact.entity_id == "entity1"
        assert fact.attribute == "price"
        assert fact.value == 100.0
        assert fact.confidence == FactConfidence.VERIFIED
        assert fact.priority == FactPriority.OFFICIAL

    def test_fact_to_dict(self):
        """Test fact to_dict"""
        fact = Fact(
            id="fact1",
            entity_id="entity1",
            attribute="price",
            value=100.0,
            source="document1",
        )

        data = fact.to_dict()
        assert data["id"] == "fact1"
        assert data["attribute"] == "price"
        assert data["value"] == 100.0


class TestCompanyBrain:
    """Test CompanyBrain"""

    @pytest.mark.asyncio
    async def test_create_entity(self, company_brain, regular_user):
        """Test create entity"""
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
            attributes={"sku": "SKU001"},
        )

        assert entity.name == "Product A"
        assert entity.entity_type == EntityType.PRODUCT
        assert entity.created_by == regular_user.id

    @pytest.mark.asyncio
    async def test_get_entity(self, company_brain, regular_user):
        """Test get entity"""
        # Create entity
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.CUSTOMER,
            name="Customer A",
        )

        # Get entity
        retrieved = await company_brain.get_entity(regular_user, entity.id)
        assert retrieved.id == entity.id
        assert retrieved.name == "Customer A"

    @pytest.mark.asyncio
    async def test_list_entities(self, company_brain, regular_user):
        """Test list entities"""
        # Create entities
        await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )
        await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.CUSTOMER,
            name="Customer A",
        )

        # List all entities
        entities = await company_brain.list_entities(regular_user)
        assert len(entities) >= 2

        # List by type
        products = await company_brain.list_entities(
            regular_user,
            entity_type=EntityType.PRODUCT,
        )
        assert all(e.entity_type == EntityType.PRODUCT for e in products)

    @pytest.mark.asyncio
    async def test_create_fact(self, company_brain, regular_user):
        """Test create fact"""
        # Create entity
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )

        # Create fact
        fact = await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="price",
            value=100.0,
            source="price_list",
            confidence=FactConfidence.VERIFIED,
            priority=FactPriority.OFFICIAL,
        )

        assert fact.entity_id == entity.id
        assert fact.attribute == "price"
        assert fact.value == 100.0
        assert fact.is_active

    @pytest.mark.asyncio
    async def test_fact_conflict_resolution(self, company_brain, regular_user):
        """Test fact conflict resolution with priority"""
        # Create entity
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )

        # Create low priority fact
        fact1 = await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="price",
            value=100.0,
            source="estimate",
            priority=FactPriority.UNVERIFIED,
        )

        assert fact1.is_active

        # Create high priority conflicting fact
        fact2 = await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="price",
            value=120.0,
            source="official_price_list",
            priority=FactPriority.OFFICIAL,
        )

        # High priority fact should be active
        assert fact2.is_active
        assert fact2.supersedes == fact1.id

        # Low priority fact should be superseded
        # Re-fetch fact1 to see database updates
        fact1_updated = await company_brain.get_fact(regular_user, fact1.id)
        assert not fact1_updated.is_active
        assert fact1_updated.superseded_by == fact2.id

    @pytest.mark.asyncio
    async def test_reject_lower_priority_fact(self, company_brain, regular_user):
        """Test rejecting lower priority fact"""
        # Create entity
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )

        # Create high priority fact
        await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="price",
            value=100.0,
            source="official",
            priority=FactPriority.OFFICIAL,
        )

        # Try to create lower priority conflicting fact
        with pytest.raises(ValidationError):
            await company_brain.create_fact(
                user=regular_user,
                entity_id=entity.id,
                attribute="price",
                value=80.0,
                source="estimate",
                priority=FactPriority.UNVERIFIED,
            )

    @pytest.mark.asyncio
    async def test_get_entity_facts(self, company_brain, regular_user):
        """Test get entity facts"""
        # Create entity
        entity = await company_brain.create_entity(
            user=regular_user,
            entity_type=EntityType.PRODUCT,
            name="Product A",
        )

        # Create facts
        await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="price",
            value=100.0,
            source="source1",
        )
        await company_brain.create_fact(
            user=regular_user,
            entity_id=entity.id,
            attribute="stock",
            value=50,
            source="source2",
        )

        # Get all facts
        facts = await company_brain.get_entity_facts(regular_user, entity.id)
        assert len(facts) == 2

        # Get facts by attribute
        price_facts = await company_brain.get_entity_facts(
            regular_user,
            entity.id,
            attribute="price",
        )
        assert len(price_facts) == 1
        assert price_facts[0].attribute == "price"
