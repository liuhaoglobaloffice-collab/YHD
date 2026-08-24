"""
Research Domain

Research-specific business operations including:
- Market research
- Competitive intelligence
- Technology research
- Trend analysis
"""

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

import structlog

from src.business.models import BusinessDomain, BusinessTask, BusinessTaskPriority
from src.business.service import BusinessService

logger = structlog.get_logger(__name__)


@dataclass
class ResearchTask:
    """Generic research task data"""

    research_type: str = ""  # market, competitor, technology, trend, etc.
    research_scope: str = ""
    target_sources: List[str] = field(default_factory=list)
    depth_level: str = "standard"  # quick, standard, deep


@dataclass
class CompetitorResearch:
    """Competitor research task data"""

    competitor_name: str = ""
    focus_areas: List[str] = field(default_factory=list)  # product, pricing, marketing, etc.
    comparison_metrics: List[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Trend analysis task data"""

    industry: str = ""
    time_period: str = ""
    trend_categories: List[str] = field(default_factory=list)


class ResearchService:
    """
    Research domain service.

    Provides research-specific task creation and management
    built on top of BusinessService.
    """

    def __init__(self, business_service: BusinessService):
        """Initialize research service"""
        self.business = business_service
        logger.info("research_service_initialized")

    async def create_research_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        research_type: str,
        research_scope: str,
        target_sources: Optional[List[str]] = None,
        depth_level: str = "standard",
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create generic research task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            research_type: Type of research
            research_scope: Scope of research
            target_sources: Optional list of sources to research
            depth_level: Depth level (quick, standard, deep)
            priority: Task priority

        Returns:
            Created business task
        """
        research_data = ResearchTask(
            research_type=research_type,
            research_scope=research_scope,
            target_sources=target_sources or [],
            depth_level=depth_level,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.RESEARCH,
            title=title,
            description=description,
            priority=priority,
            context={"research": research_data.__dict__},
            tags=["research", research_type, depth_level],
        )

        logger.info(
            f"Research task created: {title}",
            extra={
                "task_id": str(task.id),
                "type": research_type,
                "depth": depth_level,
            },
        )

        return task

    async def create_competitor_research(
        self,
        user_id: UUID,
        title: str,
        description: str,
        competitor_name: str,
        focus_areas: List[str],
        comparison_metrics: Optional[List[str]] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.HIGH,
    ) -> BusinessTask:
        """
        Create competitor research task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            competitor_name: Name of the competitor
            focus_areas: Areas to focus on (product, pricing, marketing, etc.)
            comparison_metrics: Optional metrics for comparison
            priority: Task priority

        Returns:
            Created business task
        """
        competitor_data = CompetitorResearch(
            competitor_name=competitor_name,
            focus_areas=focus_areas,
            comparison_metrics=comparison_metrics or [],
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.RESEARCH,
            title=title,
            description=description,
            priority=priority,
            context={"competitor": competitor_data.__dict__},
            tags=["research", "competitor", competitor_name] + focus_areas,
        )

        logger.info(
            f"Competitor research task created: {title}",
            extra={
                "task_id": str(task.id),
                "competitor": competitor_name,
                "focus": focus_areas,
            },
        )

        return task

    async def create_trend_analysis(
        self,
        user_id: UUID,
        title: str,
        description: str,
        industry: str,
        time_period: str,
        trend_categories: List[str],
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create trend analysis task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            industry: Industry to analyze
            time_period: Time period for analysis
            trend_categories: Categories of trends to analyze
            priority: Task priority

        Returns:
            Created business task
        """
        trend_data = TrendAnalysis(
            industry=industry,
            time_period=time_period,
            trend_categories=trend_categories,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.RESEARCH,
            title=title,
            description=description,
            priority=priority,
            context={"trend": trend_data.__dict__},
            tags=["research", "trend", industry] + trend_categories,
        )

        logger.info(
            f"Trend analysis task created: {title}",
            extra={
                "task_id": str(task.id),
                "industry": industry,
                "period": time_period,
            },
        )

        return task
