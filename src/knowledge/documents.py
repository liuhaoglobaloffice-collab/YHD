"""
Document Management System

Handles document lifecycle, versioning, and security.

P0-2: All document CRUD is persisted through DocumentRepository →
DocumentModel (database). DocumentMetadata remains the API-facing
dataclass; every read/write now goes to the database so documents
survive process restarts.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select

from ..core.errors import NotFoundError, PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService
from ..security.policy import PolicyEngine


class DocumentStatus(str, Enum):
    """Document lifecycle status"""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    AVAILABLE = "available"
    UPDATED = "updated"
    ARCHIVED = "archived"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types"""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    MARKDOWN = "markdown"
    TEXT = "text"


@dataclass
class DocumentMetadata:
    """Document metadata"""

    id: str
    filename: str
    file_type: str
    size: int
    hash: str
    source: str
    owner_id: str
    status: DocumentStatus
    version: int = 1
    parent_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    content: Optional[str] = None
    company_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "size": self.size,
            "hash": self.hash,
            "source": self.source,
            "owner_id": self.owner_id,
            "status": self.status.value,
            "version": self.version,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
            "title": self.title,
            "company_id": self.company_id,
        }


class DocumentService:
    """
    Document Service

    Manages document lifecycle with security, versioning, and audit.

    P0-2: Database-backed persistence via DocumentRepository. The
    service requires a database session; every create/update/delete/
    get/list operation is committed to the database.
    """

    # Allowed file types
    ALLOWED_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/markdown",
        "text/csv",
    }

    # File type extensions
    TYPE_EXTENSIONS = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/plain": ".txt",
        "text/markdown": ".md",
        "text/csv": ".csv",
    }

    # Max file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(
        self,
        rbac_service: RBACService,
        policy_engine: PolicyEngine,
        audit_service: AuditService,
        session=None,
    ):
        if session is None:
            raise ValidationError(
                "DocumentService requires a database session for persistence"
            )
        self.rbac = rbac_service
        self.policy = policy_engine
        self.audit = audit_service
        self.session = session

        from ..database.repositories.knowledge import DocumentRepository

        self.repository = DocumentRepository(session)

    # ------------------------------------------------------------------
    # Model <-> dataclass conversion
    # ------------------------------------------------------------------

    def _model_to_metadata(self, model) -> DocumentMetadata:
        """Convert DocumentModel to the API-facing DocumentMetadata."""
        meta = dict(model.meta or {})
        return DocumentMetadata(
            id=str(model.id),
            filename=model.filename,
            file_type=model.file_type,
            size=model.size,
            hash=meta.get("content_hash", ""),
            source=meta.get("source", "upload"),
            owner_id=str(model.created_by),
            status=DocumentStatus(model.status),
            version=meta.get("version", 1),
            parent_id=meta.get("parent_id"),
            created_at=model.created_at,
            updated_at=model.updated_at,
            metadata=meta.get("custom", {}),
            title=model.title,
            content=model.content,
            company_id=model.company_id,
        )

    @staticmethod
    def _extract_text(content: bytes) -> str:
        """Decode raw bytes to text for full-text storage."""
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return str(content)

    def validate_file(
        self,
        filename: str,
        file_type: str,
        size: int,
        content: bytes,
    ) -> None:
        """
        Validate uploaded file

        Raises:
            ValidationError: If validation fails
        """
        # File type validation
        if file_type not in self.ALLOWED_TYPES:
            raise ValidationError(
                f"File type not allowed: {file_type}",
                details={"allowed_types": list(self.ALLOWED_TYPES)},
            )

        # File size validation
        if size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds maximum: {size} > {self.MAX_FILE_SIZE}",
                details={"max_size": self.MAX_FILE_SIZE},
            )

        # Filename validation
        if not filename or len(filename) > 255:
            raise ValidationError("Invalid filename", details={"filename": filename})

        # Content hash validation
        if not content or len(content) == 0:
            raise ValidationError("Empty file content")

    def compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content"""
        return hashlib.sha256(content).hexdigest()

    async def upload_document(
        self,
        user: User,
        filename: str,
        file_type: str,
        size: int,
        content: bytes,
        source: str = "upload",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentMetadata:
        """
        Upload a new document (persisted to the database)

        Args:
            user: User uploading the document
            filename: Original filename
            file_type: MIME type
            size: File size in bytes
            content: File content
            source: Upload source
            metadata: Additional metadata

        Returns:
            DocumentMetadata: Created document metadata

        Raises:
            ValidationError: If validation fails
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="upload_document",
                resource_type="document",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Validate file
        self.validate_file(filename, file_type, size, content)

        # Policy check (PolicyEngine is synchronous: resource/action/context)
        policy_result = self.policy.evaluate(
            resource="knowledge_document",
            action="upload_document",
            context={
                "user_id": user.id,
                "filename": filename,
                "file_type": file_type,
                "size": size,
                "source": source,
            },
        )
        if not policy_result.is_allowed():
            await self.audit.log(
                action=AuditAction.ACCESS_DENIED,
                user_id=user.id,
                resource_type="document",
                details={"reason": policy_result.reason},
            )
            raise PermissionDeniedError(f"Policy denied: {policy_result.reason}")

        # Compute hash
        file_hash = self.compute_hash(content)

        # Check for duplicate by hash (database lookup)
        existing = await self._find_by_hash(file_hash)
        if existing and existing.owner_id == str(user.id):
            # Same user uploading same content - create new version
            return await self._create_version(user, existing, filename, metadata)

        # Generate document ID
        doc_id = str(uuid4())

        meta_json = {
            "content_hash": file_hash,
            "source": source,
            "version": 1,
            "parent_id": None,
            "custom": metadata or {},
        }

        # Persist document to the database
        from ..database.models import DocumentModel

        model = DocumentModel(
            id=doc_id,
            filename=filename,
            title=(metadata or {}).get("title") or filename,
            file_type=file_type,
            size=size,
            content=self._extract_text(content),
            tags=(metadata or {}).get("tags") or [],
            meta=meta_json,
            created_by=str(user.id),
            company_id=str(user.tenant_id) if getattr(user, "tenant_id", None) else None,
            content_hash=file_hash,
            status=DocumentStatus.UPLOADED.value,
        )
        model = await self.repository.create(model)
        await self.session.commit()

        doc = self._model_to_metadata(model)

        # Audit log
        await self.audit.log(
            action=AuditAction.CREATE,
            user_id=user.id,
            resource_type="document",
            resource_id=doc_id,
            details={
                "filename": filename,
                "file_type": file_type,
                "size": size,
                "hash": file_hash,
            },
        )

        return doc

    async def _find_by_hash(self, file_hash: str) -> Optional[DocumentMetadata]:
        """Find document by content hash (database query)"""
        from ..database.models import DocumentModel

        result = await self.session.execute(
            select(DocumentModel)
            .where(
                DocumentModel.content_hash == file_hash,
                DocumentModel.status != DocumentStatus.ARCHIVED.value,
            )
            .order_by(DocumentModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_metadata(model)

    async def _create_version(
        self,
        user: User,
        parent: DocumentMetadata,
        filename: str,
        metadata: Optional[Dict[str, Any]],
    ) -> DocumentMetadata:
        """Create a new version of existing document (database-backed)"""
        from ..database.models import DocumentModel

        # Archive the parent document in the database
        parent_model = await self.repository.get_by_id(parent.id)
        if parent_model is None:
            raise NotFoundError(f"Parent document not found: {parent.id}")
        parent_model.status = DocumentStatus.ARCHIVED.value
        await self.session.flush()

        new_version = parent.version + 1
        version_id = str(uuid4())

        meta_json = {
            "content_hash": parent.hash,
            "source": parent.source,
            "version": new_version,
            "parent_id": parent.id,
            "custom": metadata or parent.metadata,
        }

        model = DocumentModel(
            id=version_id,
            filename=filename,
            title=(metadata or {}).get("title") or filename,
            file_type=parent.file_type,
            size=parent.size,
            content=parent.content,
            tags=(metadata or {}).get("tags") or [],
            meta=meta_json,
            created_by=str(user.id),
            company_id=parent.company_id,
            content_hash=parent.hash,
            status=DocumentStatus.UPLOADED.value,
        )
        model = await self.repository.create(model)
        await self.session.commit()

        # Audit log
        await self.audit.log(
            action=AuditAction.UPDATE,
            user_id=user.id,
            resource_type="document",
            resource_id=parent.id,
            details={
                "action": "create_version",
                "new_version": new_version,
                "version_id": version_id,
            },
        )

        return self._model_to_metadata(model)

    async def get_document(
        self,
        user: User,
        document_id: str,
    ) -> DocumentMetadata:
        """
        Get document metadata (database query)

        Args:
            user: User requesting the document
            document_id: Document ID

        Returns:
            DocumentMetadata: Document metadata

        Raises:
            NotFoundError: If document not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="get_document",
                resource_type="document",
                resource_id=document_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Find document in the database
        model = await self.repository.get_by_id(document_id)
        if not model:
            raise NotFoundError(f"Document not found: {document_id}")

        # Owner or admin can access
        if str(model.created_by) != str(user.id) and not self.rbac.is_admin(user):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="get_document",
                resource_type="document",
                resource_id=document_id,
            )
            raise PermissionDeniedError("User cannot access this document")

        # Audit log
        await self.audit.log(
            action=AuditAction.READ,
            user_id=user.id,
            resource_type="document",
            resource_id=document_id,
        )

        return self._model_to_metadata(model)

    async def list_documents(
        self,
        user: User,
        status: Optional[DocumentStatus] = None,
        owner_id: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[DocumentMetadata]:
        """
        List documents (database query)

        Args:
            user: User requesting the list
            status: Filter by status
            owner_id: Filter by owner
            file_type: Filter by MIME file type
            limit: Maximum number of documents

        Returns:
            List[DocumentMetadata]: List of documents

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_READ):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="list_documents",
                resource_type="document",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        from ..database.models import DocumentModel

        conditions = []
        # Tenant isolation: non-admin users only see their own documents
        if not self.rbac.is_admin(user):
            conditions.append(DocumentModel.created_by == str(user.id))
        if status:
            conditions.append(DocumentModel.status == status.value)
        if owner_id:
            conditions.append(DocumentModel.created_by == owner_id)
        if file_type:
            conditions.append(DocumentModel.file_type == file_type)

        stmt = select(DocumentModel).order_by(DocumentModel.created_at.desc()).limit(limit)
        if conditions:
            from sqlalchemy import and_

            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        models = list(result.scalars().all())

        return [self._model_to_metadata(m) for m in models]

    async def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> None:
        """
        Update document status (database update)

        Args:
            document_id: Document ID
            status: New status

        Raises:
            NotFoundError: If document not found
        """
        model = await self.repository.get_by_id(document_id)
        if not model:
            raise NotFoundError(f"Document not found: {document_id}")

        model.status = status.value
        await self.session.flush()
        await self.session.commit()

    async def delete_document(
        self,
        user: User,
        document_id: str,
    ) -> None:
        """
        Delete document (soft delete - archive, database update)

        Args:
            user: User deleting the document
            document_id: Document ID

        Raises:
            NotFoundError: If document not found
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="delete_document",
                resource_type="document",
                resource_id=document_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")

        # Find document in the database
        model = await self.repository.get_by_id(document_id)
        if not model:
            raise NotFoundError(f"Document not found: {document_id}")

        # Owner or admin can delete
        if str(model.created_by) != str(user.id) and not self.rbac.is_admin(user):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="delete_document",
                resource_type="document",
                resource_id=document_id,
            )
            raise PermissionDeniedError("User cannot delete this document")

        # Soft delete - archive
        model.status = DocumentStatus.ARCHIVED.value
        await self.session.flush()
        await self.session.commit()

        # Audit log
        await self.audit.log(
            action=AuditAction.DELETE,
            user_id=user.id,
            resource_type="document",
            resource_id=document_id,
        )
