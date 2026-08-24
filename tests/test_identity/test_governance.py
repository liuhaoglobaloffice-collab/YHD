"""
Tests for Identity Governance Service
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import PermissionDeniedError, ResourceNotFoundError
from src.identity.governance import IdentityGovernanceService
from src.identity.models import RoleEnum, Session, User


@pytest.mark.asyncio
class TestIdentityGovernanceService:
    """Test IdentityGovernanceService functionality"""

    async def test_get_user(self, async_session: AsyncSession, admin_user: User):
        """Test getting user by ID"""
        service = IdentityGovernanceService(async_session)

        user = await service.get_user(admin_user.id)
        assert user.id == admin_user.id
        assert user.username == admin_user.username

    async def test_get_user_not_found(self, async_session: AsyncSession):
        """Test getting non-existent user"""
        service = IdentityGovernanceService(async_session)

        with pytest.raises(ResourceNotFoundError):
            await service.get_user(99999)

    async def test_get_user_by_username(self, async_session: AsyncSession, admin_user: User):
        """Test getting user by username"""
        service = IdentityGovernanceService(async_session)

        user = await service.get_user_by_username(admin_user.username)
        assert user is not None
        assert user.id == admin_user.id

    async def test_get_user_by_username_not_found(self, async_session: AsyncSession):
        """Test getting non-existent username"""
        service = IdentityGovernanceService(async_session)

        user = await service.get_user_by_username("nonexistent_user")
        assert user is None

    async def test_disable_user(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test admin disabling a target user"""
        service = IdentityGovernanceService(async_session)

        disabled_user = await service.disable_user(target_user.id, admin_user)

        assert disabled_user.is_active is False
        assert disabled_user.id == target_user.id

    async def test_enable_user(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test admin enabling a target user"""
        service = IdentityGovernanceService(async_session)

        # First disable
        await service.disable_user(target_user.id, admin_user)

        # Then enable
        enabled_user = await service.enable_user(target_user.id, admin_user)

        assert enabled_user.is_active is True

    async def test_disable_user_revokes_sessions(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test that disabling target user revokes all their sessions"""
        service = IdentityGovernanceService(async_session)

        # Create a session for target_user
        from datetime import UTC, datetime, timedelta

        session = Session(
            user_id=target_user.id,
            token_jti="test_jti_123",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async_session.add(session)
        await async_session.commit()

        # Disable user
        await service.disable_user(target_user.id, admin_user)

        # Check session is revoked
        await async_session.refresh(session)
        assert session.is_active is False
        assert session.revoked_at is not None

    async def test_change_user_role(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test admin changing target user role"""
        service = IdentityGovernanceService(async_session)

        # Change to viewer
        updated_user = await service.change_user_role(
            user_id=target_user.id,
            new_role=RoleEnum.VIEWER,
            actor=admin_user,
        )

        assert updated_user.role == RoleEnum.VIEWER

    async def test_cannot_change_last_admin_role(
        self, async_session: AsyncSession, admin_user: User
    ):
        """Test protection against removing last admin"""
        service = IdentityGovernanceService(async_session)

        # Try to change the only admin to user
        with pytest.raises(PermissionDeniedError, match="Cannot change role of last admin"):
            await service.change_user_role(
                user_id=admin_user.id,
                new_role=RoleEnum.USER,
                actor=admin_user,
            )

    async def test_revoke_user_sessions(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test revoking all user sessions"""
        service = IdentityGovernanceService(async_session)

        # Create multiple sessions
        from datetime import UTC, datetime, timedelta

        session1 = Session(
            user_id=admin_user.id,
            token_jti="jti_1",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session2 = Session(
            user_id=admin_user.id,
            token_jti="jti_2",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async_session.add_all([session1, session2])
        await async_session.commit()

        # Revoke sessions
        count = await service.revoke_user_sessions(admin_user.id, admin_user)

        assert count == 2

        # Check sessions are revoked
        await async_session.refresh(session1)
        await async_session.refresh(session2)
        assert session1.is_active is False
        assert session2.is_active is False

    async def test_revoke_specific_session(
        self, async_session: AsyncSession, admin_user: User, target_user: User
    ):
        """Test revoking a specific session"""
        service = IdentityGovernanceService(async_session)

        # Create session
        from datetime import UTC, datetime, timedelta

        session = Session(
            user_id=admin_user.id,
            token_jti="jti_specific",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async_session.add(session)
        await async_session.commit()

        # Revoke by JTI
        revoked = await service.revoke_session_by_jti("jti_specific", admin_user)

        assert revoked is True
        await async_session.refresh(session)
        assert session.is_active is False

    async def test_revoke_session_not_found(self, async_session: AsyncSession, admin_user: User):
        """Test revoking non-existent session"""
        service = IdentityGovernanceService(async_session)

        revoked = await service.revoke_session_by_jti("nonexistent_jti", admin_user)
        assert revoked is False

    async def test_validate_session_active(self, async_session: AsyncSession, admin_user: User):
        """Test validating active session"""
        service = IdentityGovernanceService(async_session)

        # Create active session
        from datetime import UTC, datetime, timedelta

        session = Session(
            user_id=admin_user.id,
            token_jti="jti_valid",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async_session.add(session)
        await async_session.commit()

        # Validate
        is_valid = await service.validate_session("jti_valid")
        assert is_valid is True

    async def test_validate_session_expired(self, async_session: AsyncSession, admin_user: User):
        """Test validating expired session"""
        service = IdentityGovernanceService(async_session)

        # Create expired session
        from datetime import UTC, datetime, timedelta

        session = Session(
            user_id=admin_user.id,
            token_jti="jti_expired",
            is_active=True,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        async_session.add(session)
        await async_session.commit()

        # Validate
        is_valid = await service.validate_session("jti_expired")
        assert is_valid is False

    async def test_validate_session_revoked(self, async_session: AsyncSession, admin_user: User):
        """Test validating revoked session"""
        service = IdentityGovernanceService(async_session)

        # Create revoked session
        from datetime import UTC, datetime, timedelta

        session = Session(
            user_id=admin_user.id,
            token_jti="jti_revoked",
            is_active=False,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            revoked_at=datetime.now(UTC),
        )
        async_session.add(session)
        await async_session.commit()

        # Validate
        is_valid = await service.validate_session("jti_revoked")
        assert is_valid is False
