"""
Marketing Domain

Marketing-specific business operations including:
- SEO tasks
- Content creation
- Market analysis
- Campaign management
"""

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

import structlog

from src.business.models import BusinessDomain, BusinessTask, BusinessTaskPriority
from src.business.service import BusinessService

logger = structlog.get_logger(__name__)


@dataclass
class SEOTask:
    """SEO-specific task data"""

    target_keywords: List[str] = field(default_factory=list)
    target_url: Optional[str] = None
    current_rank: Optional[int] = None
    target_rank: Optional[int] = None
    competitors: List[str] = field(default_factory=list)


@dataclass
class ContentTask:
    """Content creation task data"""

    content_type: str = ""  # blog, article, social, video, etc.
    topic: str = ""
    target_audience: str = ""
    word_count: Optional[int] = None
    style_guide: Optional[str] = None


@dataclass
class MarketAnalysisTask:
    """Market analysis task data"""

    market_segment: str = ""
    analysis_type: str = ""  # competitor, trend, opportunity, etc.
    time_period: Optional[str] = None
    competitors: List[str] = field(default_factory=list)


class MarketingService:
    """
    Marketing domain service.

    Provides marketing-specific task creation and management
    built on top of BusinessService.
    """

    def __init__(self, business_service: BusinessService):
        """Initialize marketing service"""
        self.business = business_service
        logger.info("marketing_service_initialized")

    async def create_seo_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        target_keywords: List[str],
        target_url: Optional[str] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create SEO optimization task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            target_keywords: Keywords to target
            target_url: URL to optimize
            priority: Task priority

        Returns:
            Created business task
        """
        seo_data = SEOTask(
            target_keywords=target_keywords,
            target_url=target_url,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title=title,
            description=description,
            priority=priority,
            context={"seo": seo_data.__dict__},
            tags=["seo", "optimization"] + target_keywords,
        )

        logger.info(
            f"SEO task created: {title}",
            extra={
                "task_id": str(task.id),
                "keywords": target_keywords,
            },
        )

        return task

    async def create_content_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        content_type: str,
        topic: str,
        target_audience: str,
        word_count: Optional[int] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create content creation task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            content_type: Type of content (blog, article, social, etc.)
            topic: Content topic
            target_audience: Target audience
            word_count: Optional target word count
            priority: Task priority

        Returns:
            Created business task
        """
        content_data = ContentTask(
            content_type=content_type,
            topic=topic,
            target_audience=target_audience,
            word_count=word_count,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title=title,
            description=description,
            priority=priority,
            context={"content": content_data.__dict__},
            tags=["content", content_type, topic],
        )

        logger.info(
            f"Content task created: {title}",
            extra={
                "task_id": str(task.id),
                "content_type": content_type,
                "topic": topic,
            },
        )

        return task

    async def create_market_analysis_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        market_segment: str,
        analysis_type: str,
        competitors: Optional[List[str]] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.HIGH,
    ) -> BusinessTask:
        """
        Create market analysis task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            market_segment: Market segment to analyze
            analysis_type: Type of analysis (competitor, trend, opportunity, etc.)
            competitors: Optional list of competitors
            priority: Task priority

        Returns:
            Created business task
        """
        analysis_data = MarketAnalysisTask(
            market_segment=market_segment,
            analysis_type=analysis_type,
            competitors=competitors or [],
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title=title,
            description=description,
            priority=priority,
            context={"analysis": analysis_data.__dict__},
            tags=["analysis", analysis_type, market_segment],
        )

        logger.info(
            f"Market analysis task created: {title}",
            extra={
                "task_id": str(task.id),
                "segment": market_segment,
                "type": analysis_type,
            },
        )

        return task
