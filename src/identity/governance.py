"""
Identity Governance - User lifecycle and session management
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.identity.models import RoleEnum, Session, User

logger = structlog.get_logger(__name__)


def _ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert naive datetime to UTC aware datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class IdentityGovernanceService:
    """
    Identity Governance Service

    Manages user lifecycle, status, roles, and session governance.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("identity_governance_initialized")

    async def get_user(self, user_id: int) -> User:
        """Get user by ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("user_not_found", user_id=user_id)
            raise ResourceNotFoundError(f"User {user_id} not found")

        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def enable_user(self, user_id: int, actor: User) -> User:
        """
        Enable a user account

        Args:
            user_id: User to enable
            actor: User performing the action

        Returns:
            Updated user
        """
        user = await self.get_user(user_id)

        if user.is_active:
            logger.info("user_already_enabled", user_id=user_id)
            return user

        user.is_active = True
        user.updated_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(
            "user_enabled",
            user_id=user_id,
            actor_id=actor.id,
        )

        return user

    async def disable_user(self, user_id: int, actor: User) -> User:
        """
        Disable a user account

        Args:
            user_id: User to disable
            actor: User performing the action

        Returns:
            Updated user
        """
        user = await self.get_user(user_id)

        # Prevent self-disable for admins
        if user.id == actor.id and user.role == RoleEnum.ADMIN:
            logger.warning(
                "admin_self_disable_prevented",
                user_id=user_id,
            )
            raise ValidationError("Admin cannot disable their own account")

        if not user.is_active:
            logger.info("user_already_disabled", user_id=user_id)
            return user

        user.is_active = False
        user.updated_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(user)

        # Revoke all active sessions
        await self.revoke_user_sessions(user_id, actor)

        logger.info(
            "user_disabled",
            user_id=user_id,
            actor_id=actor.id,
        )

        return user

    async def change_user_role(
        self,
        user_id: int,
        new_role: RoleEnum,
        actor: User,
    ) -> User:
        """
        Change user role

        Args:
            user_id: User to update
            new_role: New role
            actor: User performing the action

        Returns:
            Updated user
        """
        user = await self.get_user(user_id)

        old_role = user.role

        # Prevent last admin from losing admin role
        if old_role == RoleEnum.ADMIN and new_role != RoleEnum.ADMIN:
            admin_count = await self._count_admins()
            if admin_count <= 1:
                logger.warning(
                    "last_admin_role_change_prevented",
                    user_id=user_id,
                )
                raise PermissionDeniedError("Cannot change role of last admin")

        user.role = new_role
        user.updated_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(
            "user_role_changed",
            user_id=user_id,
            old_role=old_role,
            new_role=new_role,
            actor_id=actor.id,
        )

        return user

    async def _count_admins(self) -> int:
        """Count active admin users"""
        result = await self.session.execute(
            select(User).where(
                User.role == RoleEnum.ADMIN,
                User.is_active,
            )
        )
        return len(result.scalars().all())

    async def create_session(
        self,
        user: User,
        token_jti: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_in_minutes: int = 60,
    ) -> Session:
        """
        Create a session for tracking

        Args:
            user: User
            token_jti: JWT token ID (jti claim)
            ip_address: Client IP
            user_agent: Client user agent
            expires_in_minutes: Session expiration in minutes

        Returns:
            Created session
        """
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)

        session = Session(
            user_id=user.id,
            token_jti=token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=expires_at,
        )

        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)

        logger.info(
            "session_created",
            session_id=session.id,
            user_id=user.id,
            expires_at=expires_at,
        )

        return session

    async def get_session_by_jti(self, token_jti: str) -> Optional[Session]:
        """Get session by JWT token ID"""
        result = await self.session.execute(select(Session).where(Session.token_jti == token_jti))
        return result.scalar_one_or_none()

    async def validate_session(self, token_jti: str) -> bool:
        """
        Validate if session is active and not expired

        Returns:
            True if valid, False otherwise
        """
        session = await self.get_session_by_jti(token_jti)

        if not session:
            logger.debug("session_not_found", token_jti=token_jti)
            return False

        if not session.is_active:
            logger.debug("session_inactive", session_id=session.id)
            return False

        if session.revoked_at:
            logger.debug("session_revoked", session_id=session.id)
            return False

        if datetime.now(UTC) > _ensure_utc_aware(session.expires_at):
            logger.debug("session_expired", session_id=session.id)
            return False

        logger.debug("session_valid", session_id=session.id)
        return True

    async def revoke_session(self, token_jti: str, actor: User) -> None:
        """
        Revoke a specific session

        Args:
            token_jti: JWT token ID to revoke
            actor: User performing the action
        """
        session = await self.get_session_by_jti(token_jti)

        if not session:
            logger.warning("revoke_session_not_found", token_jti=token_jti)
            return

        if session.revoked_at:
            logger.info("session_already_revoked", session_id=session.id)
            return

        session.is_active = False
        session.revoked_at = datetime.now(UTC)

        await self.session.commit()

        logger.info(
            "session_revoked",
            session_id=session.id,
            user_id=session.user_id,
            actor_id=actor.id,
        )

    async def revoke_session_by_jti(self, token_jti: str, actor: User) -> bool:
        """
        Revoke a specific session by JTI

        Args:
            token_jti: JWT token ID to revoke
            actor: User performing the action

        Returns:
            True if session was revoked, False if not found
        """
        session = await self.get_session_by_jti(token_jti)

        if not session:
            logger.warning("revoke_session_not_found", token_jti=token_jti)
            return False

        if session.revoked_at:
            logger.info("session_already_revoked", session_id=session.id)
            return True

        session.is_active = False
        session.revoked_at = datetime.now(UTC)

        await self.session.commit()

        logger.info(
            "session_revoked",
            session_id=session.id,
            user_id=session.user_id,
            actor_id=actor.id,
        )
        return True

    async def revoke_user_sessions(self, user_id: int, actor: User) -> int:
        """
        Revoke all active sessions for a user

        Args:
            user_id: User whose sessions to revoke
            actor: User performing the action

        Returns:
            Number of sessions revoked
        """
        result = await self.session.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_active,
            )
        )
        sessions = result.scalars().all()

        count = 0
        for session in sessions:
            session.is_active = False
            session.revoked_at = datetime.now(UTC)
            count += 1

        await self.session.commit()

        logger.info(
            "user_sessions_revoked",
            user_id=user_id,
            count=count,
            actor_id=actor.id,
        )

        return count

    async def list_user_sessions(
        self,
        user_id: int,
        active_only: bool = True,
    ) -> list[Session]:
        """
        List sessions for a user

        Args:
            user_id: User ID
            active_only: Filter only active sessions

        Returns:
            List of sessions
        """
        query = select(Session).where(Session.user_id == user_id)

        if active_only:
            query = query.where(Session.is_active)

        query = query.order_by(Session.created_at.desc())

        result = await self.session.execute(query)
        sessions = result.scalars().all()

        logger.debug(
            "user_sessions_listed",
            user_id=user_id,
            count=len(sessions),
            active_only=active_only,
        )

        return list(sessions)
