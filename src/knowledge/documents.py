"""
Document Management System

Handles document lifecycle, versioning, and security.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.errors import NotFoundError, PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService
from ..security.policy import PolicyContext, PolicyEngine


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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class DocumentService:
    """
    Document Service

    Manages document lifecycle with security, versioning, and audit.
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
    ):
        self.rbac = rbac_service
        self.policy = policy_engine
        self.audit = audit_service

        # In-memory storage (will be replaced with database in production)
        self._documents: Dict[str, DocumentMetadata] = {}

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
        Upload a new document

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

        # Policy check
        policy_context = PolicyContext(
            user_id=user.id,
            action="upload_document",
            resource_type="document",
            resource_id=None,
            metadata={
                "filename": filename,
                "file_type": file_type,
                "size": size,
                "source": source,
            },
        )

        policy_result = await self.policy.evaluate(policy_context)
        if not policy_result.allowed:
            await self.audit.log(
                action=AuditAction.ACCESS_DENIED,
                user_id=user.id,
                resource_type="document",
                details={"reason": policy_result.reason},
            )
            raise PermissionDeniedError(f"Policy denied: {policy_result.reason}")

        # Compute hash
        file_hash = self.compute_hash(content)

        # Check for duplicate by hash
        existing = self._find_by_hash(file_hash)
        if existing and existing.owner_id == user.id:
            # Same user uploading same content - create new version
            return await self._create_version(user, existing, filename, metadata)

        # Generate document ID
        doc_id = f"doc_{datetime.now(UTC).timestamp()}_{user.id}"

        # Create document metadata
        doc = DocumentMetadata(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            size=size,
            hash=file_hash,
            source=source,
            owner_id=user.id,
            status=DocumentStatus.UPLOADED,
            metadata=metadata or {},
        )

        # Store document
        self._documents[doc_id] = doc

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

    def _find_by_hash(self, file_hash: str) -> Optional[DocumentMetadata]:
        """Find document by content hash"""
        for doc in self._documents.values():
            if doc.hash == file_hash and doc.status != DocumentStatus.ARCHIVED:
                return doc
        return None

    async def _create_version(
        self,
        user: User,
        parent: DocumentMetadata,
        filename: str,
        metadata: Optional[Dict[str, Any]],
    ) -> DocumentMetadata:
        """Create a new version of existing document"""
        # Generate version ID
        version_id = f"{parent.id}_v{parent.version + 1}"

        # Create new version
        new_version = DocumentMetadata(
            id=version_id,
            filename=filename,
            file_type=parent.file_type,
            size=parent.size,
            hash=parent.hash,
            source=parent.source,
            owner_id=user.id,
            status=DocumentStatus.UPLOADED,
            version=parent.version + 1,
            parent_id=parent.id,
            metadata=metadata or parent.metadata,
        )

        # Update parent status
        parent.status = DocumentStatus.ARCHIVED
        parent.updated_at = datetime.now(UTC)

        # Store new version
        self._documents[version_id] = new_version

        # Audit log
        await self.audit.log(
            action=AuditAction.UPDATE,
            user_id=user.id,
            resource_type="document",
            resource_id=parent.id,
            details={
                "action": "create_version",
                "new_version": new_version.version,
                "version_id": version_id,
            },
        )

        return new_version

    async def get_document(
        self,
        user: User,
        document_id: str,
    ) -> DocumentMetadata:
        """
        Get document metadata

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

        # Find document
        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")

        # Owner or admin can access
        if doc.owner_id != user.id and not self.rbac.is_admin(user):
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

        return doc

    async def list_documents(
        self,
        user: User,
        status: Optional[DocumentStatus] = None,
        owner_id: Optional[str] = None,
    ) -> List[DocumentMetadata]:
        """
        List documents

        Args:
            user: User requesting the list
            status: Filter by status
            owner_id: Filter by owner

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

        # Filter documents
        docs = []
        for doc in self._documents.values():
            # Owner or admin can see
            if doc.owner_id != user.id and not self.rbac.is_admin(user):
                continue

            # Status filter
            if status and doc.status != status:
                continue

            # Owner filter
            if owner_id and doc.owner_id != owner_id:
                continue

            docs.append(doc)

        return docs

    async def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
    ) -> None:
        """
        Update document status (internal use)

        Args:
            document_id: Document ID
            status: New status
        """
        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")

        doc.status = status
        doc.updated_at = datetime.now(UTC)

    async def delete_document(
        self,
        user: User,
        document_id: str,
    ) -> None:
        """
        Delete document (soft delete - archive)

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

        # Find document
        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")

        # Owner or admin can delete
        if doc.owner_id != user.id and not self.rbac.is_admin(user):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="delete_document",
                resource_type="document",
                resource_id=document_id,
            )
            raise PermissionDeniedError("User cannot delete this document")

        # Soft delete - archive
        doc.status = DocumentStatus.ARCHIVED
        doc.updated_at = datetime.now(UTC)

        # Audit log
        await self.audit.log(
            action=AuditAction.DELETE,
            user_id=user.id,
            resource_type="document",
            resource_id=document_id,
        )
