"""
Tests for Document Management
"""


import pytest

from src.core.errors import ValidationError
from src.identity.models import RoleEnum, User
from src.identity.rbac import Permission
from src.knowledge.documents import (
    DocumentMetadata,
    DocumentService,
    DocumentStatus,
)


@pytest.fixture
def admin_user():
    """Admin user fixture"""
    return User(
        id=1,
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )


@pytest.fixture
def regular_user():
    """Regular user fixture"""
    return User(
        id=2,
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
            if user.role == RoleEnum.ADMIN:
                return True
            if permission in [Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE]:
                return True
            return False

        def is_admin(self, user):
            return user.role == RoleEnum.ADMIN

    return MockRBAC()


@pytest.fixture
def mock_policy():
    """Mock policy engine"""

    class MockPolicy:
        async def evaluate(self, context):
            from src.security.policy import PolicyResult

            return PolicyResult(allowed=True, reason="Mock allowed")

    return MockPolicy()


@pytest.fixture
def mock_audit():
    """Mock audit service"""

    class MockAudit:
        async def log(self, action, user_id, resource_type, resource_id=None, details=None):
            pass

        async def log_permission_denied(self, user_id, action, resource_type, resource_id=None):
            pass

    return MockAudit()


@pytest.fixture
def document_service(mock_rbac, mock_policy, mock_audit):
    """Document service fixture"""
    return DocumentService(
        rbac_service=mock_rbac,
        policy_engine=mock_policy,
        audit_service=mock_audit,
    )


class TestDocumentMetadata:
    """Test DocumentMetadata"""

    def test_metadata_creation(self):
        """Test metadata creation"""
        metadata = DocumentMetadata(
            id="doc1",
            filename="test.txt",
            file_type="text/plain",
            size=1024,
            hash="abc123",
            source="upload",
            owner_id="user1",
            status=DocumentStatus.UPLOADED,
        )

        assert metadata.id == "doc1"
        assert metadata.filename == "test.txt"
        assert metadata.file_type == "text/plain"
        assert metadata.size == 1024
        assert metadata.hash == "abc123"
        assert metadata.status == DocumentStatus.UPLOADED
        assert metadata.version == 1

    def test_metadata_to_dict(self):
        """Test metadata to_dict"""
        metadata = DocumentMetadata(
            id="doc1",
            filename="test.txt",
            file_type="text/plain",
            size=1024,
            hash="abc123",
            source="upload",
            owner_id="user1",
            status=DocumentStatus.UPLOADED,
        )

        data = metadata.to_dict()
        assert data["id"] == "doc1"
        assert data["filename"] == "test.txt"
        assert data["status"] == "uploaded"


class TestDocumentService:
    """Test DocumentService"""

    def test_validate_file_type(self, document_service):
        """Test file type validation"""
        # Valid file type
        document_service.validate_file(
            filename="test.txt",
            file_type="text/plain",
            size=1024,
            content=b"test content",
        )

        # Invalid file type
        with pytest.raises(ValidationError):
            document_service.validate_file(
                filename="test.exe",
                file_type="application/x-executable",
                size=1024,
                content=b"test content",
            )

    def test_validate_file_size(self, document_service):
        """Test file size validation"""
        # Valid size
        document_service.validate_file(
            filename="test.txt",
            file_type="text/plain",
            size=1024,
            content=b"test content",
        )

        # Too large
        with pytest.raises(ValidationError):
            document_service.validate_file(
                filename="test.txt",
                file_type="text/plain",
                size=100 * 1024 * 1024,  # 100MB
                content=b"test content",
            )

    def test_compute_hash(self, document_service):
        """Test hash computation"""
        content = b"test content"
        hash1 = document_service.compute_hash(content)
        hash2 = document_service.compute_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_upload_document(self, document_service, regular_user):
        """Test document upload"""
        doc = await document_service.upload_document(
            user=regular_user,
            filename="test.txt",
            file_type="text/plain",
            size=100,
            content=b"test content",
            source="upload",
        )

        assert doc.filename == "test.txt"
        assert doc.owner_id == regular_user.id
        assert doc.status == DocumentStatus.UPLOADED
        assert doc.version == 1

    @pytest.mark.asyncio
    async def test_upload_duplicate_creates_version(self, document_service, regular_user):
        """Test uploading duplicate creates version"""
        content = b"test content"

        # Upload first time
        doc1 = await document_service.upload_document(
            user=regular_user,
            filename="test.txt",
            file_type="text/plain",
            size=len(content),
            content=content,
        )

        # Upload same content again
        doc2 = await document_service.upload_document(
            user=regular_user,
            filename="test_v2.txt",
            file_type="text/plain",
            size=len(content),
            content=content,
        )

        assert doc2.version == 2
        assert doc2.parent_id == doc1.id
        assert doc1.status == DocumentStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_get_document(self, document_service, regular_user):
        """Test get document"""
        # Upload document
        doc = await document_service.upload_document(
            user=regular_user,
            filename="test.txt",
            file_type="text/plain",
            size=100,
            content=b"test content",
        )

        # Get document
        retrieved = await document_service.get_document(regular_user, doc.id)
        assert retrieved.id == doc.id
        assert retrieved.filename == doc.filename

    @pytest.mark.asyncio
    async def test_list_documents(self, document_service, regular_user):
        """Test list documents"""
        # Upload multiple documents
        await document_service.upload_document(
            user=regular_user,
            filename="test1.txt",
            file_type="text/plain",
            size=100,
            content=b"content1",
        )
        await document_service.upload_document(
            user=regular_user,
            filename="test2.txt",
            file_type="text/plain",
            size=100,
            content=b"content2",
        )

        # List documents
        docs = await document_service.list_documents(regular_user)
        assert len(docs) >= 2

    @pytest.mark.asyncio
    async def test_delete_document(self, document_service, regular_user):
        """Test delete document"""
        # Upload document
        doc = await document_service.upload_document(
            user=regular_user,
            filename="test.txt",
            file_type="text/plain",
            size=100,
            content=b"test content",
        )

        # Delete document
        await document_service.delete_document(regular_user, doc.id)

        # Verify archived
        retrieved = await document_service.get_document(regular_user, doc.id)
        assert retrieved.status == DocumentStatus.ARCHIVED
