"""
Company Brain

Structured enterprise knowledge and facts.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.errors import NotFoundError, PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService


class EntityType(str, Enum):
    """Entity type"""

    COMPANY = "company"
    PRODUCT = "product"
    MARKET = "market"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PERSON = "person"
    LOCATION = "location"
    EVENT = "event"


class FactConfidence(str, Enum):
    """Fact confidence level"""

    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class FactPriority(int, Enum):
    """Fact priority (higher = more authoritative)"""

    OFFICIAL = 100
    APPROVED = 80
    VERIFIED = 60
    TRUSTED = 40
    UNVERIFIED = 20
    INFERRED = 10


@dataclass
class Entity:
    """Entity in company brain"""

    id: str
    entity_type: EntityType
    name: str

    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }


@dataclass
class Fact:
    """Fact about an entity"""

    id: str
    entity_id: str
    attribute: str
    value: Any

    # Source
    source: str
    source_document_id: Optional[str] = None
    source_document_version: Optional[int] = None

    # Confidence and priority
    confidence: FactConfidence = FactConfidence.UNKNOWN
    priority: FactPriority = FactPriority.UNVERIFIED

    # Status
    is_active: bool = True

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: Optional[str] = None

    # Conflicting facts
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "attribute": self.attribute,
            "value": self.value,
            "source": self.source,
            "source_document_id": self.source_document_id,
            "source_document_version": self.source_document_version,
            "confidence": self.confidence.value,
            "priority": self.priority.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
        }


class CompanyBrain:
    """
    Company Brain

    Manages structured enterprise knowledge.
    """

    def __init__(
        self,
        session,  # AsyncSession
        rbac_service: RBACService,
        audit_service: AuditService,
        company_id: str = "default-company",  # Default company for testing
    ):
        # Phase 4: Database integration
        self.session = session
        from ..database.repositories.knowledge import (
            CompanyBrainEntityRepository,
            CompanyBrainFactRepository,
        )

        self.repository = CompanyBrainEntityRepository(session)
        self.fact_repository = CompanyBrainFactRepository(session)

        self.rbac = rbac_service
        self.audit = audit_service
        self.company_id = company_id

    def _model_to_entity(self, model) -> Entity:
        """Convert CompanyBrainEntityModel to Entity dataclass"""
        return Entity(
            id=str(model.id),
            entity_type=EntityType(model.entity_type),
            name=model.name,
            attributes=model.attributes or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=str(model.created_by) if model.created_by else None,
        )

    def _model_to_fact(self, model) -> Fact:
        """Convert CompanyBrainFactModel to Fact dataclass"""
        return Fact(
            id=str(model.id),
            entity_id=str(model.entity_id),
            attribute=model.attribute,
            value=model.value,
            source=model.source,
            source_document_id=model.source_document_id,
            source_document_version=model.source_document_version,
            confidence=FactConfidence(model.confidence),
            priority=FactPriority(model.priority),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=str(model.created_by) if model.created_by else None,
            supersedes=model.supersedes,
            superseded_by=model.superseded_by,
        )

    async def create_entity(
        self,
        user: User,
        entity_type: EntityType,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """
        Create a new entity

        Args:
            user: User creating the entity
            entity_type: Entity type
            name: Entity name
            attributes: Entity attributes

        Returns:
            Entity: Created entity

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="create_entity",
                resource_type="entity",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Validate name
        if not name or len(name.strip()) == 0:
            raise ValidationError("Entity name cannot be empty")

        # Generate entity ID
        from uuid import uuid4

        entity_id = str(uuid4())

        # Create entity
        entity = Entity(
            id=entity_id,
            entity_type=entity_type,
            name=name,
            attributes=attributes or {},
            created_by=user.id,
        )

        # Store entity
        # Store in database
        from ..database.models import CompanyBrainEntityModel

        model = CompanyBrainEntityModel(
            id=entity_id,
            entity_type=entity_type.value,
            name=name,
            attributes=attributes,
            company_id=self.company_id,
            created_by=user.id,
        )
        model = await self.repository.create(model)
        await self.session.commit()
        entity = self._model_to_entity(model)

        # Audit log
        await self.audit.log(
            session=self.session,
            action=AuditAction.CREATE,
            status="success",
            user_id=user.id,
            resource_type="entity",
            resource_id=entity_id,
            details={
                "entity_type": entity_type.value,
                "name": name,
            },
        )

        return entity

    async def get_entity(
        self,
        user: User,
        entity_id: str,
    ) -> Entity:
        """
        Get entity by ID

        Args:
            user: User requesting the entity
            entity_id: Entity ID

        Returns:
            Entity: Entity

        Raises:
            NotFoundError: If entity not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="get_entity",
                resource_type="entity",
                resource_id=entity_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Query database for entity
        model = await self.repository.get_by_id(entity_id)
        if not model:
            raise NotFoundError(f"Entity not found: {entity_id}")

        entity = self._model_to_entity(model)

        return entity

    async def list_entities(
        self,
        user: User,
        entity_type: Optional[EntityType] = None,
    ) -> List[Entity]:
        """
        List entities

        Args:
            user: User requesting the list
            entity_type: Filter by entity type

        Returns:
            List[Entity]: List of entities

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="list_entities",
                resource_type="entity",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Query database for entities
        from sqlalchemy import select

        from ..database.models import CompanyBrainEntityModel

        # Build query
        stmt = select(CompanyBrainEntityModel).where(
            CompanyBrainEntityModel.company_id == self.company_id
        )

        if entity_type:
            stmt = stmt.where(CompanyBrainEntityModel.entity_type == entity_type.value)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        entities = [self._model_to_entity(model) for model in models]

        return entities

    async def update_entity(
        self,
        user: User,
        entity_id: str,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """
        Update an entity

        Args:
            user: User updating the entity
            entity_id: Entity ID
            name: New name (optional)
            attributes: New attributes (optional)

        Returns:
            Entity: Updated entity

        Raises:
            NotFoundError: If entity not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="update_entity",
                resource_type="entity",
                resource_id=entity_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Verify entity exists
        existing = await self.repository.get_by_id(entity_id)
        if not existing:
            raise NotFoundError(f"Entity not found: {entity_id}")

        # Build update values
        values: Dict[str, Any] = {}
        if name is not None:
            if len(name.strip()) == 0:
                raise ValidationError("Entity name cannot be empty")
            values["name"] = name
        if attributes is not None:
            values["attributes"] = attributes

        if not values:
            return self._model_to_entity(existing)

        # Update in database
        model = await self.repository.update(entity_id, values)
        if not model:
            raise NotFoundError(f"Entity not found: {entity_id}")
        await self.session.commit()
        await self.session.refresh(model)
        entity = self._model_to_entity(model)

        # Audit log
        await self.audit.log(
            session=self.session,
            action=AuditAction.UPDATE,
            status="success",
            user_id=user.id,
            resource_type="entity",
            resource_id=entity_id,
            details={"updated_fields": list(values.keys())},
        )

        return entity

    async def delete_entity(
        self,
        user: User,
        entity_id: str,
    ) -> bool:
        """
        Delete an entity

        Args:
            user: User deleting the entity
            entity_id: Entity ID

        Returns:
            bool: True if deleted

        Raises:
            NotFoundError: If entity not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="delete_entity",
                resource_type="entity",
                resource_id=entity_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Verify entity exists
        existing = await self.repository.get_by_id(entity_id)
        if not existing:
            raise NotFoundError(f"Entity not found: {entity_id}")

        # Delete from database
        deleted = await self.repository.delete(entity_id)
        await self.session.commit()

        if deleted:
            await self.audit.log(
                session=self.session,
                action=AuditAction.DELETE,
                status="success",
                user_id=user.id,
                resource_type="entity",
                resource_id=entity_id,
            )

        return deleted

    async def create_fact(
        self,
        user: User,
        entity_id: str,
        attribute: str,
        value: Any,
        source: str,
        confidence: FactConfidence = FactConfidence.UNKNOWN,
        priority: FactPriority = FactPriority.UNVERIFIED,
        source_document_id: Optional[str] = None,
        source_document_version: Optional[int] = None,
    ) -> Fact:
        """
        Create a new fact

        Args:
            user: User creating the fact
            entity_id: Entity ID
            attribute: Fact attribute
            value: Fact value
            source: Fact source
            confidence: Fact confidence
            priority: Fact priority
            source_document_id: Source document ID
            source_document_version: Source document version

        Returns:
            Fact: Created fact

        Raises:
            PermissionDeniedError: If user lacks permission
            NotFoundError: If entity not found
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="create_fact",
                resource_type="fact",
                reason="User lacks KNOWLEDGE_WRITE permission",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Verify entity exists
        entity_model = await self.repository.get_by_id(entity_id)
        if not entity_model:
            raise NotFoundError(f"Entity not found: {entity_id}")

        # Validate attribute
        if not attribute or len(attribute.strip()) == 0:
            raise ValidationError("Fact attribute cannot be empty")

        # Check for conflicting facts
        existing_fact_models = await self.fact_repository.list_by_entity(
            entity_id=entity_id,
            attribute=attribute,
            active_only=True,
        )
        conflicting_fact = None

        for existing_fact_model in existing_fact_models:
            if existing_fact_model.value != value:
                # Found conflicting fact
                if priority.value > existing_fact_model.priority:
                    # New fact has higher priority - supersede old fact
                    conflicting_fact = existing_fact_model
                elif priority.value < existing_fact_model.priority:
                    # Existing fact has higher priority - reject new fact
                    await self.audit.log(
                        session=self.session,
                        action=AuditAction.CREATE,
                        status="rejected",
                        user_id=user.id,
                        resource_type="fact",
                        details={
                            "reason": "lower_priority_than_existing",
                            "entity_id": entity_id,
                            "attribute": attribute,
                            "value": value,
                            "existing_priority": existing_fact_model.priority,
                            "new_priority": priority.value,
                        },
                    )
                    raise ValidationError(
                        f"Conflicting fact with higher priority exists: {existing_fact_model.id}"
                    )

        # Generate fact ID
        import uuid

        fact_id = str(uuid.uuid4())

        # Create fact
        from ..database.models import CompanyBrainFactModel

        fact_model = CompanyBrainFactModel(
            id=fact_id,
            entity_id=entity_id,
            attribute=attribute,
            value=value,
            source=source,
            source_document_id=source_document_id,
            source_document_version=source_document_version,
            confidence=confidence.value,
            priority=priority.value,
            company_id=self.company_id,
            created_by=str(user.id),
        )

        # Handle conflict
        if conflicting_fact:
            # Supersede old fact
            conflicting_fact.is_active = False
            conflicting_fact.superseded_by = fact_id
            conflicting_fact.updated_at = datetime.now(UTC)

            # Set supersedes on new fact
            fact_model.supersedes = conflicting_fact.id

            # Audit conflict
            await self.audit.log(
                session=self.session,
                action=AuditAction.UPDATE,
                status="success",
                user_id=user.id,
                resource_type="fact",
                resource_id=conflicting_fact.id,
                details={
                    "action": "superseded",
                    "superseded_by": fact_id,
                    "reason": "higher_priority_fact",
                },
            )

        # Store fact
        fact_model = await self.fact_repository.create(fact_model)
        await self.session.commit()
        fact = self._model_to_fact(fact_model)

        # Audit log
        await self.audit.log(
            session=self.session,
            action=AuditAction.CREATE,
            status="success",
            user_id=user.id,
            resource_type="fact",
            resource_id=fact_id,
            details={
                "entity_id": entity_id,
                "attribute": attribute,
                "confidence": confidence.value,
                "priority": priority.value,
            },
        )

        return fact

    async def get_entity_facts(
        self,
        user: User,
        entity_id: str,
        attribute: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Fact]:
        """
        Get facts for an entity

        Args:
            user: User requesting the facts
            entity_id: Entity ID
            attribute: Filter by attribute
            include_inactive: Include inactive facts

        Returns:
            List[Fact]: List of facts

        Raises:
            PermissionDeniedError: If user lacks permission
            NotFoundError: If entity not found
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="get_entity_facts",
                resource_type="fact",
                reason="User lacks KNOWLEDGE_READ permission",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Verify entity exists
        entity_model = await self.repository.get_by_id(entity_id)
        if not entity_model:
            raise NotFoundError(f"Entity not found: {entity_id}")

        # Query facts from database
        fact_models = await self.fact_repository.list_by_entity(
            entity_id=entity_id,
            attribute=attribute,
            active_only=not include_inactive,
        )

        facts = [self._model_to_fact(model) for model in fact_models]

        return facts

    async def get_fact(
        self,
        user: User,
        fact_id: str,
    ) -> Fact:
        """
        Get fact by ID

        Args:
            user: User requesting the fact
            fact_id: Fact ID

        Returns:
            Fact: Fact

        Raises:
            NotFoundError: If fact not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="get_fact",
                resource_type="fact",
                reason="User lacks KNOWLEDGE_READ permission",
                resource_id=fact_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        fact_model = await self.fact_repository.get_by_id(fact_id)
        if not fact_model:
            raise NotFoundError(f"Fact not found: {fact_id}")

        fact = self._model_to_fact(fact_model)
        return fact

    async def update_fact(
        self,
        user: User,
        fact_id: str,
        value: Any = None,
        confidence: Optional[FactConfidence] = None,
        priority: Optional[FactPriority] = None,
        is_active: Optional[bool] = None,
    ) -> Fact:
        """
        Update a fact

        Args:
            user: User updating the fact
            fact_id: Fact ID
            value: New value (optional)
            confidence: New confidence (optional)
            priority: New priority (optional)
            is_active: New active status (optional)

        Returns:
            Fact: Updated fact

        Raises:
            NotFoundError: If fact not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="update_fact",
                resource_type="fact",
                reason="User lacks KNOWLEDGE_WRITE permission",
                resource_id=fact_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Verify fact exists
        existing = await self.fact_repository.get_by_id(fact_id)
        if not existing:
            raise NotFoundError(f"Fact not found: {fact_id}")

        # Build update values
        values: Dict[str, Any] = {}
        if value is not None:
            values["value"] = value
        if confidence is not None:
            values["confidence"] = confidence.value
        if priority is not None:
            values["priority"] = priority.value
        if is_active is not None:
            values["is_active"] = is_active

        if not values:
            return self._model_to_fact(existing)

        # Update in database
        model = await self.fact_repository.update(fact_id, values)
        if not model:
            raise NotFoundError(f"Fact not found: {fact_id}")
        await self.session.commit()
        await self.session.refresh(model)
        fact = self._model_to_fact(model)

        # Audit log
        await self.audit.log(
            session=self.session,
            action=AuditAction.UPDATE,
            status="success",
            user_id=user.id,
            resource_type="fact",
            resource_id=fact_id,
            details={"updated_fields": list(values.keys())},
        )

        return fact

    async def delete_fact(
        self,
        user: User,
        fact_id: str,
    ) -> bool:
        """
        Delete a fact

        Args:
            user: User deleting the fact
            fact_id: Fact ID

        Returns:
            bool: True if deleted

        Raises:
            NotFoundError: If fact not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="delete_fact",
                resource_type="fact",
                reason="User lacks KNOWLEDGE_WRITE permission",
                resource_id=fact_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Verify fact exists
        existing = await self.fact_repository.get_by_id(fact_id)
        if not existing:
            raise NotFoundError(f"Fact not found: {fact_id}")

        # Delete from database
        deleted = await self.fact_repository.delete(fact_id)
        await self.session.commit()

        if deleted:
            await self.audit.log(
                session=self.session,
                action=AuditAction.DELETE,
                status="success",
                user_id=user.id,
                resource_type="fact",
                resource_id=fact_id,
            )

        return deleted
