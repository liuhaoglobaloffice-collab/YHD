"""
Tests for Audit Service
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.audit import AuditService
from src.identity.models import User


@pytest.mark.asyncio
class TestAuditService:
    """Test AuditService functionality"""

    async def test_log_basic(self, async_session: AsyncSession, test_user: User):
        """Test basic audit logging"""
        log = await AuditService.log(
            session=async_session,
            action="test_action",
            resource_type="test_resource",
            status="success",
            user_id=test_user.id,
            resource_id="123",
        )

        assert log.id is not None
        assert log.action == "test_action"
        assert log.resource_type == "test_resource"
        assert log.status == "success"
        assert log.user_id == test_user.id
        assert log.resource_id == "123"

    async def test_log_success(self, async_session: AsyncSession, test_user: User):
        """Test log_success helper"""
        log = await AuditService.log_success(
            session=async_session,
            action="create_user",
            resource_type="user",
            user_id=test_user.id,
            resource_id="456",
            details={"username": "newuser"},
        )

        assert log.status == "success"
        assert log.action == "create_user"

    async def test_log_failure(self, async_session: AsyncSession, test_user: User):
        """Test log_failure helper"""
        log = await AuditService.log_failure(
            session=async_session,
            action="delete_user",
            resource_type="user",
            error_message="User not found",
            user_id=test_user.id,
            resource_id="999",
        )

        assert log.status == "failure"
        assert log.error_message == "User not found"

    async def test_log_denied(self, async_session: AsyncSession, test_user: User):
        """Test log_denied helper"""
        log = await AuditService.log_denied(
            session=async_session,
            action="update_role",
            resource_type="user",
            reason="Insufficient permissions",
            user_id=test_user.id,
        )

        assert log.status == "denied"
        assert log.error_message == "Insufficient permissions"

    async def test_sanitize_password(self, async_session: AsyncSession, test_user: User):
        """Test that passwords are sanitized"""
        log = await AuditService.log(
            session=async_session,
            action="create_user",
            resource_type="user",
            status="success",
            user_id=test_user.id,
            details={
                "username": "newuser",
                "password": "secret123",
                "email": "user@example.com",
            },
        )

        assert log.details["password"] == "[REDACTED]"
        assert log.details["username"] == "newuser"
        assert log.details["email"] == "user@example.com"

    async def test_sanitize_token(self, async_session: AsyncSession, test_user: User):
        """Test that tokens are sanitized"""
        log = await AuditService.log(
            session=async_session,
            action="api_call",
            resource_type="external",
            status="success",
            user_id=test_user.id,
            details={
                "api_key": "sk_test_123456",
                "access_token": "bearer_token_xyz",
                "endpoint": "/api/data",
            },
        )

        assert log.details["api_key"] == "[REDACTED]"
        assert log.details["access_token"] == "[REDACTED]"
        assert log.details["endpoint"] == "/api/data"

    async def test_sanitize_nested_secrets(self, async_session: AsyncSession, test_user: User):
        """Test sanitization of nested secrets"""
        log = await AuditService.log(
            session=async_session,
            action="configure",
            resource_type="system",
            status="success",
            user_id=test_user.id,
            details={
                "config": {
                    "database_url": "postgres://...",
                    "secret_key": "secret123",
                    "api_keys": {
                        "openai": "sk-xxx",
                        "stripe": "sk_live_yyy",
                    },
                },
                "public_setting": "value",
            },
        )

        assert log.details["config"]["secret_key"] == "[REDACTED]"
        assert log.details["config"]["api_keys"]["openai"] == "[REDACTED]"
        assert log.details["config"]["database_url"] == "postgres://..."
        assert log.details["public_setting"] == "value"

    async def test_sanitize_list_of_dicts(self, async_session: AsyncSession, test_user: User):
        """Test sanitization in lists"""
        log = await AuditService.log(
            session=async_session,
            action="bulk_create",
            resource_type="user",
            status="success",
            user_id=test_user.id,
            details={
                "users": [
                    {"username": "user1", "password": "pass1"},
                    {"username": "user2", "password": "pass2"},
                ],
            },
        )

        assert log.details["users"][0]["password"] == "[REDACTED]"
        assert log.details["users"][1]["password"] == "[REDACTED]"
        assert log.details["users"][0]["username"] == "user1"

    async def test_log_login(self, async_session: AsyncSession, test_user: User):
        """Test log_login helper"""
        log = await AuditService.log_login(
            session=async_session,
            user_id=test_user.id,
            success=True,
            ip_address="192.168.1.1",
        )

        assert log.action == "login"
        assert log.status == "success"
        assert log.ip_address == "192.168.1.1"

    async def test_log_login_failure(self, async_session: AsyncSession, test_user: User):
        """Test login failure logging"""
        log = await AuditService.log_login(
            session=async_session,
            user_id=test_user.id,
            success=False,
            error_message="Invalid password",
        )

        assert log.status == "failure"
        assert log.error_message == "Invalid password"

    async def test_log_logout(self, async_session: AsyncSession, test_user: User):
        """Test log_logout helper"""
        log = await AuditService.log_logout(
            session=async_session,
            user_id=test_user.id,
        )

        assert log.action == "logout"
        assert log.status == "success"

    async def test_log_permission_denied(self, async_session: AsyncSession, test_user: User):
        """Test log_permission_denied helper"""
        log = await AuditService.log_permission_denied(
            session=async_session,
            user_id=test_user.id,
            action="delete_user",
            resource_type="user",
            reason="User role is not admin",
            resource_id="789",
        )

        assert log.action == "delete_user"
        assert log.status == "denied"
        assert log.error_message == "User role is not admin"

    async def test_log_role_change(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test log_role_change helper"""
        log = await AuditService.log_role_change(
            session=async_session,
            actor_id=admin_user.id,
            target_user_id=test_user.id,
            old_role="user",
            new_role="admin",
        )

        assert log.action == "change_role"
        assert log.user_id == admin_user.id
        assert log.resource_id == str(test_user.id)
        assert log.details["old_role"] == "user"
        assert log.details["new_role"] == "admin"

    async def test_log_approval(self, async_session: AsyncSession, admin_user: User):
        """Test log_approval helper"""
        log = await AuditService.log_approval(
            session=async_session,
            approver_id=admin_user.id,
            request_id=123,
            action="approve",
            decision="approved",
        )

        assert log.action == "approval_approve"
        assert log.resource_type == "approval_request"
        assert log.details["decision"] == "approved"

    async def test_log_session_revoked(
        self, async_session: AsyncSession, admin_user: User, test_user: User
    ):
        """Test log_session_revoked helper"""
        log = await AuditService.log_session_revoked(
            session=async_session,
            actor_id=admin_user.id,
            target_user_id=test_user.id,
            session_count=3,
        )

        assert log.action == "revoke_sessions"
        assert log.resource_type == "session"
        assert log.details["session_count"] == 3

    async def test_query_logs_basic(self, async_session: AsyncSession, test_user: User):
        """Test querying audit logs"""
        # Create some logs
        await AuditService.log_success(
            session=async_session,
            action="read",
            resource_type="data",
            user_id=test_user.id,
        )
        await AuditService.log_failure(
            session=async_session,
            action="write",
            resource_type="data",
            user_id=test_user.id,
            error_message="Permission denied",
        )

        # Query all logs for user
        logs = await AuditService.query_logs(session=async_session, user_id=test_user.id)

        assert len(logs) >= 2
        assert all(log.user_id == test_user.id for log in logs)

    async def test_query_logs_filter_action(self, async_session: AsyncSession, test_user: User):
        """Test filtering logs by action"""
        await AuditService.log(
            session=async_session,
            action="login",
            resource_type="user",
            status="success",
            user_id=test_user.id,
        )
        await AuditService.log(
            session=async_session,
            action="logout",
            resource_type="user",
            status="success",
            user_id=test_user.id,
        )

        # Query only login actions
        logs = await AuditService.query_logs(
            session=async_session,
            user_id=test_user.id,
            action="login",
        )

        assert all(log.action == "login" for log in logs)

    async def test_query_logs_filter_status(self, async_session: AsyncSession, test_user: User):
        """Test filtering logs by status"""
        await AuditService.log_success(
            session=async_session,
            action="test1",
            resource_type="test",
            user_id=test_user.id,
        )
        await AuditService.log_failure(
            session=async_session,
            action="test2",
            resource_type="test",
            user_id=test_user.id,
            error_message="Failed",
        )

        # Query only failures
        logs = await AuditService.query_logs(
            session=async_session,
            user_id=test_user.id,
            status="failure",
        )

        assert all(log.status == "failure" for log in logs)

    async def test_query_logs_limit(self, async_session: AsyncSession, test_user: User):
        """Test query limit"""
        # Create multiple logs
        for i in range(10):
            await AuditService.log_success(
                session=async_session,
                action=f"action_{i}",
                resource_type="test",
                user_id=test_user.id,
            )

        # Query with limit
        logs = await AuditService.query_logs(
            session=async_session,
            user_id=test_user.id,
            limit=5,
        )

        assert len(logs) <= 5
