"""
Approval System - Unified approval workflow
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.governance.risk import RiskEvaluator
from src.identity.models import ApprovalRequest, ApprovalStatus, RiskLevel, User

logger = structlog.get_logger(__name__)


def _ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert naive datetime to UTC aware datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ApprovalService:
    """
    Unified Approval System

    Handles creation, approval, rejection, and lifecycle of approval requests.
    This service determines "whether to allow execution" but does NOT execute
    the actual business logic.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.risk_evaluator = RiskEvaluator()
        logger.debug("approval_service_initialized")

    async def create_request(
        self,
        requester: User,
        request_type: str,
        target_resource: str,
        target_action: str,
        target_id: Optional[str] = None,
        payload: Optional[dict] = None,
        reason: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ApprovalRequest:
        """
        Create an approval request

        Args:
            requester: User creating the request
            request_type: Type of request
            target_resource: Resource being operated on
            target_action: Action to perform
            target_id: Optional resource ID
            payload: Request payload/parameters
            reason: Reason for the request
            context: Additional context for risk evaluation

        Returns:
            Created ApprovalRequest
        """
        # Evaluate risk
        risk_level = self.risk_evaluator.evaluate(
            request_type=request_type,
            resource=target_resource,
            action=target_action,
            context=context or {},
        )

        # Set expiration (24 hours for high/critical, 7 days for medium/low)
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            expires_at = datetime.now(UTC) + timedelta(hours=24)
        else:
            expires_at = datetime.now(UTC) + timedelta(days=7)

        # Create request
        approval_request = ApprovalRequest(
            request_type=request_type,
            requester_id=requester.id,
            target_resource=target_resource,
            target_action=target_action,
            target_id=target_id,
            payload=payload,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            reason=reason,
            expires_at=expires_at,
        )

        self.session.add(approval_request)
        await self.session.commit()
        await self.session.refresh(approval_request)

        logger.info(
            "approval_request_created",
            request_id=approval_request.id,
            requester_id=requester.id,
            request_type=request_type,
            risk_level=risk_level,
            expires_at=expires_at,
        )

        return approval_request

    async def get_request(self, request_id: int) -> ApprovalRequest:
        """Get approval request by ID"""
        result = await self.session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            logger.warning("approval_request_not_found", request_id=request_id)
            raise ResourceNotFoundError(f"Approval request {request_id} not found")

        return request

    async def approve(
        self,
        request_id: int,
        approver: User,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Approve a request

        Args:
            request_id: Request ID
            approver: User approving the request
            review_reason: Reason for approval

        Returns:
            Updated ApprovalRequest

        Raises:
            ValidationError: If request cannot be approved
            PermissionDeniedError: If approver lacks permission
        """
        request = await self.get_request(request_id)

        # Validate state
        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                "approval_invalid_state",
                request_id=request_id,
                current_status=request.status,
            )
            raise ValidationError(f"Cannot approve request with status: {request.status}")

        # Check expiration
        if request.expires_at and datetime.now(UTC) > _ensure_utc_aware(request.expires_at):
            request.status = ApprovalStatus.EXPIRED
            await self.session.commit()
            logger.warning("approval_expired", request_id=request_id)
            raise ValidationError("Approval request has expired")

        # Prevent self-approval for high/critical risk
        if request.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if request.requester_id == approver.id:
                logger.warning(
                    "approval_self_approval_denied",
                    request_id=request_id,
                    user_id=approver.id,
                )
                raise PermissionDeniedError("Cannot self-approve high/critical risk requests")

        # Update request
        request.status = ApprovalStatus.APPROVED
        request.approver_id = approver.id
        request.review_reason = reason
        request.reviewed_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(request)

        logger.info(
            "approval_request_approved",
            request_id=request_id,
            approver_id=approver.id,
            risk_level=request.risk_level,
        )

        return request

    async def reject(
        self,
        request_id: int,
        approver: User,
        reason: str,
    ) -> ApprovalRequest:
        """
        Reject a request

        Args:
            request_id: Request ID
            approver: User rejecting the request
            review_reason: Reason for rejection (required)

        Returns:
            Updated ApprovalRequest
        """
        if not reason:
            raise ValidationError("Rejection reason is required")

        request = await self.get_request(request_id)

        # Validate state
        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                "rejection_invalid_state",
                request_id=request_id,
                current_status=request.status,
            )
            raise ValidationError(f"Cannot reject request with status: {request.status}")

        # Update request
        request.status = ApprovalStatus.REJECTED
        request.approver_id = approver.id
        request.review_reason = reason
        request.reviewed_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(request)

        logger.info(
            "approval_request_rejected",
            request_id=request_id,
            approver_id=approver.id,
        )

        return request

    async def cancel(
        self,
        request_id: int,
        canceller: User,
    ) -> ApprovalRequest:
        """
        Cancel a request (requester only)

        Args:
            request_id: Request ID
            canceller: User cancelling the request

        Returns:
            Updated ApprovalRequest
        """
        request = await self.get_request(request_id)

        # Only requester can cancel
        if request.requester_id != canceller.id:
            logger.warning(
                "approval_cancel_unauthorized",
                request_id=request_id,
                user_id=canceller.id,
                requester_id=request.requester_id,
            )
            raise PermissionDeniedError("Only requester can cancel the request")

        # Validate state
        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                "cancel_invalid_state",
                request_id=request_id,
                current_status=request.status,
            )
            raise ValidationError(f"Cannot cancel request with status: {request.status}")

        # Update request
        request.status = ApprovalStatus.CANCELLED
        request.reviewed_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(request)

        logger.info("approval_request_cancelled", request_id=request_id)

        return request

    async def check_auto_approval(
        self,
        requester: User,
        request_type: str,
        target_resource: str,
        target_action: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Check if operation can be auto-approved (low risk)

        Returns:
            True if auto-approved, False if manual approval needed
        """
        risk_level = self.risk_evaluator.evaluate(
            request_type=request_type,
            resource=target_resource,
            action=target_action,
            context=context or {},
        )

        requires_approval = self.risk_evaluator.requires_approval(risk_level)

        logger.info(
            "auto_approval_check",
            requester_id=requester.id,
            request_type=request_type,
            risk_level=risk_level,
            requires_approval=requires_approval,
        )

        return not requires_approval

    async def list_pending(
        self,
        user: Optional[User] = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        """
        List pending approval requests

        Args:
            user: Optional filter by requester
            limit: Max results

        Returns:
            List of pending requests
        """
        query = select(ApprovalRequest).where(ApprovalRequest.status == ApprovalStatus.PENDING)

        if user:
            query = query.where(ApprovalRequest.requester_id == user.id)

        query = query.order_by(ApprovalRequest.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        requests = result.scalars().all()

        logger.debug(
            "pending_approvals_listed",
            count=len(requests),
            user_id=user.id if user else None,
        )

        return list(requests)

    async def list_requests(
        self,
        user: Optional[User] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """
        List all approval requests with optional filters

        Args:
            user: Optional filter by requester
            status: Optional filter by status
            limit: Max results

        Returns:
            List of approval requests
        """
        query = select(ApprovalRequest)

        if user:
            query = query.where(ApprovalRequest.requester_id == user.id)

        if status:
            query = query.where(ApprovalRequest.status == status)

        query = query.order_by(ApprovalRequest.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        requests = result.scalars().all()

        logger.debug(
            "approval_requests_listed",
            count=len(requests),
            user_id=user.id if user else None,
            status=status,
        )

        return list(requests)

    async def is_approved(self, request_id: int) -> bool:
        """
        Check if an action is approved

        Args:
            request_id: Approval request ID

        Returns:
            True if approved, False otherwise
        """
        try:
            request = await self.get_request(request_id)

            # Check if expired and update status
            if request.status == ApprovalStatus.PENDING:
                if request.expires_at and datetime.now(UTC) > _ensure_utc_aware(request.expires_at):
                    request.status = ApprovalStatus.EXPIRED
                    await self.session.commit()
                    return False

            return request.status == ApprovalStatus.APPROVED
        except ResourceNotFoundError:
            return False
