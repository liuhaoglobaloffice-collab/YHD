"""
Tests for Approval System
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import PermissionDeniedError, ValidationError
from src.governance.approval import ApprovalService
from src.identity.models import ApprovalStatus, RiskLevel, User


@pytest.mark.asyncio
class TestApprovalService:
    """Test ApprovalService functionality"""

    async def test_create_low_risk_approval(self, async_session: AsyncSession, test_user: User):
        """Test creating low-risk approval request (auto-approved)"""
        service = ApprovalService(async_session)

        request = await service.create_request(
            requester=test_user,
            request_type="data_read",
            target_resource="report",
            target_action="generate",
            reason="Generate monthly report",
        )

        assert request.id is not None
        assert request.requester_id == test_user.id
        assert request.risk_level == RiskLevel.LOW
        # Low risk may be auto-approved based on config
        assert request.status in [ApprovalStatus.PENDING, ApprovalStatus.APPROVED]

    async def test_create_high_risk_approval(self, async_session: AsyncSession, test_user: User):
        """Test creating high-risk approval request"""
        service = ApprovalService(async_session)

        request = await service.create_request(
            requester=test_user,
            request_type="user_delete",
            target_resource="user",
            target_action="delete",
            target_id="123",
            reason="Delete inactive user",
        )

        assert request.id is not None
        assert request.risk_level == RiskLevel.HIGH
        assert request.status == ApprovalStatus.PENDING
        assert request.expires_at is not None
        assert request.approver_id is None

    async def test_create_critical_risk_approval(
        self, async_session: AsyncSession, test_user: User
    ):
        """Test creating critical-risk approval request"""
        service = ApprovalService(async_session)

        request = await service.create_request(
            requester=test_user,
            request_type="system_shutdown",
            target_resource="system",
            target_action="shutdown",
            reason="Emergency maintenance",
        )

        assert request.risk_level == RiskLevel.CRITICAL
        assert request.status == ApprovalStatus.PENDING

    async def test_approve_request(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test approving a request"""
        service = ApprovalService(async_session)

        # Create request
        request = await service.create_request(
            requester=test_user,
            request_type="user_role_change",
            target_resource="user",
            target_action="update_role",
            target_id="456",
        )

        # Approve
        approved = await service.approve(
            request_id=request.id,
            approver=admin_user,
            reason="Approved after verification",
        )

        assert approved.status == ApprovalStatus.APPROVED
        assert approved.approver_id == admin_user.id
        assert approved.review_reason == "Approved after verification"
        assert approved.reviewed_at is not None

    async def test_reject_request(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test rejecting a request"""
        service = ApprovalService(async_session)

        # Create request
        request = await service.create_request(
            requester=test_user,
            request_type="data_export",
            target_resource="data",
            target_action="export_all",
        )

        # Reject
        rejected = await service.reject(
            request_id=request.id,
            approver=admin_user,
            reason="Insufficient justification",
        )

        assert rejected.status == ApprovalStatus.REJECTED
        assert rejected.approver_id == admin_user.id
        assert rejected.review_reason == "Insufficient justification"

    async def test_cancel_request(self, async_session: AsyncSession, test_user: User):
        """Test cancelling a request by requester"""
        service = ApprovalService(async_session)

        # Create request
        request = await service.create_request(
            requester=test_user,
            request_type="user_disable",
            target_resource="user",
            target_action="disable",
            target_id="789",
        )

        # Cancel
        cancelled = await service.cancel(
            request_id=request.id,
            canceller=test_user,
        )

        assert cancelled.status == ApprovalStatus.CANCELLED

    async def test_cannot_cancel_others_request(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test that users cannot cancel others' requests"""
        service = ApprovalService(async_session)

        # Create request as test_user
        request = await service.create_request(
            requester=test_user,
            request_type="test",
            target_resource="resource",
            target_action="action",
        )

        # Try to cancel as different user
        with pytest.raises(PermissionDeniedError):
            await service.cancel(request_id=request.id, canceller=admin_user)

    async def test_prevent_self_approval_high_risk(
        self, async_session: AsyncSession, test_user: User
    ):
        """Test that users cannot approve their own HIGH/CRITICAL risk requests"""
        service = ApprovalService(async_session)

        # Create HIGH risk request
        request = await service.create_request(
            requester=test_user,
            request_type="user_delete",
            target_resource="user",
            target_action="delete",
        )

        # Try to self-approve
        with pytest.raises(PermissionDeniedError, match="Cannot self-approve"):
            await service.approve(request_id=request.id, approver=test_user)

    async def test_cannot_approve_non_pending(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test that only PENDING requests can be approved"""
        service = ApprovalService(async_session)

        # Create and approve request
        request = await service.create_request(
            requester=test_user,
            request_type="user_disable",
            target_resource="user",
            target_action="disable",
        )
        await service.approve(request_id=request.id, approver=admin_user)

        # Try to approve again
        with pytest.raises(ValidationError, match="Cannot approve request"):
            await service.approve(request_id=request.id, approver=admin_user)

    async def test_check_expired_requests(self, async_session: AsyncSession, test_user: User):
        """Test expiration checking"""
        service = ApprovalService(async_session)

        # Create request with short expiration
        request = await service.create_request(
            requester=test_user,
            request_type="test",
            target_resource="resource",
            target_action="action",
        )

        # Manually set expired time
        request.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await async_session.commit()
        await async_session.refresh(request)

        # Check if approved should detect expiration
        result = await service.is_approved(request.id)
        assert result is False

        # Refresh and check status updated to EXPIRED
        await async_session.refresh(request)
        assert request.status == ApprovalStatus.EXPIRED

    async def test_is_approved(
        self, async_session: AsyncSession, test_user: User, admin_user: User
    ):
        """Test is_approved method"""
        service = ApprovalService(async_session)

        # Create and approve request
        request = await service.create_request(
            requester=test_user,
            request_type="user_disable",
            target_resource="user",
            target_action="disable",
        )
        await service.approve(request_id=request.id, approver=admin_user)

        # Check
        assert await service.is_approved(request.id) is True

    async def test_is_not_approved(self, async_session: AsyncSession, test_user: User):
        """Test is_approved returns False for pending/rejected"""
        service = ApprovalService(async_session)

        # Pending request
        request = await service.create_request(
            requester=test_user,
            request_type="user_delete",
            target_resource="user",
            target_action="delete",
        )

        assert await service.is_approved(request.id) is False

    async def test_payload_stored(self, async_session: AsyncSession, test_user: User):
        """Test that payload is properly stored"""
        service = ApprovalService(async_session)

        payload = {"user_id": 123, "new_role": "admin", "reason": "promotion"}

        request = await service.create_request(
            requester=test_user,
            request_type="role_change",
            target_resource="user",
            target_action="update_role",
            payload=payload,
        )

        assert request.payload == payload
