"""
Sales Domain

Sales-specific business operations including:
- Lead management
- Customer outreach
- Deal tracking
- Sales analysis
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import structlog

from src.business.models import BusinessDomain, BusinessTask, BusinessTaskPriority
from src.business.service import BusinessService

logger = structlog.get_logger(__name__)


@dataclass
class LeadTask:
    """Lead management task data"""

    lead_source: str = ""
    lead_stage: str = ""  # new, contacted, qualified, etc.
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    estimated_value: Optional[float] = None


@dataclass
class OutreachTask:
    """Customer outreach task data"""

    outreach_type: str = ""  # email, call, meeting, etc.
    target_segment: str = ""
    message_template: Optional[str] = None
    target_count: Optional[int] = None


@dataclass
class DealTask:
    """Deal tracking task data"""

    deal_stage: str = ""  # proposal, negotiation, closing, etc.
    deal_value: Optional[float] = None
    probability: Optional[float] = None
    expected_close_date: Optional[str] = None


class SalesService:
    """
    Sales domain service.

    Provides sales-specific task creation and management
    built on top of BusinessService.
    """

    def __init__(self, business_service: BusinessService):
        """Initialize sales service"""
        self.business = business_service
        logger.info("sales_service_initialized")

    async def create_lead_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        lead_source: str,
        lead_stage: str,
        company_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        estimated_value: Optional[float] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.HIGH,
    ) -> BusinessTask:
        """
        Create lead management task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            lead_source: Source of the lead
            lead_stage: Current stage of the lead
            company_name: Optional company name
            contact_name: Optional contact name
            estimated_value: Optional estimated deal value
            priority: Task priority

        Returns:
            Created business task
        """
        lead_data = LeadTask(
            lead_source=lead_source,
            lead_stage=lead_stage,
            company_name=company_name,
            contact_name=contact_name,
            estimated_value=estimated_value,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.SALES,
            title=title,
            description=description,
            priority=priority,
            context={"lead": lead_data.__dict__},
            tags=["lead", lead_source, lead_stage],
        )

        logger.info(
            f"Lead task created: {title}",
            extra={
                "task_id": str(task.id),
                "lead_source": lead_source,
                "company": company_name,
            },
        )

        return task

    async def create_outreach_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        outreach_type: str,
        target_segment: str,
        target_count: Optional[int] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create customer outreach task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            outreach_type: Type of outreach (email, call, meeting, etc.)
            target_segment: Target customer segment
            target_count: Optional target contact count
            priority: Task priority

        Returns:
            Created business task
        """
        outreach_data = OutreachTask(
            outreach_type=outreach_type,
            target_segment=target_segment,
            target_count=target_count,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.SALES,
            title=title,
            description=description,
            priority=priority,
            context={"outreach": outreach_data.__dict__},
            tags=["outreach", outreach_type, target_segment],
        )

        logger.info(
            f"Outreach task created: {title}",
            extra={
                "task_id": str(task.id),
                "type": outreach_type,
                "segment": target_segment,
            },
        )

        return task

    async def create_deal_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        deal_stage: str,
        deal_value: Optional[float] = None,
        probability: Optional[float] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.URGENT,
    ) -> BusinessTask:
        """
        Create deal tracking task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            deal_stage: Current deal stage
            deal_value: Optional deal value
            probability: Optional probability of closing (0.0 to 1.0)
            priority: Task priority

        Returns:
            Created business task
        """
        deal_data = DealTask(
            deal_stage=deal_stage,
            deal_value=deal_value,
            probability=probability,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.SALES,
            title=title,
            description=description,
            priority=priority,
            context={"deal": deal_data.__dict__},
            tags=["deal", deal_stage],
        )

        logger.info(
            f"Deal task created: {title}",
            extra={
                "task_id": str(task.id),
                "stage": deal_stage,
                "value": deal_value,
            },
        )

        return task
