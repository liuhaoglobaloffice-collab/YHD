"""
Operations Domain

Operations-specific business operations including:
- Process automation
- Data processing
- System monitoring
- Workflow optimization
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.business.models import BusinessDomain, BusinessTask, BusinessTaskPriority
from src.business.service import BusinessService

logger = structlog.get_logger(__name__)


@dataclass
class AutomationTask:
    """Process automation task data"""

    process_name: str = ""
    automation_type: str = ""  # workflow, script, integration, etc.
    trigger: Optional[str] = None
    frequency: Optional[str] = None  # once, daily, weekly, etc.


@dataclass
class DataProcessingTask:
    """Data processing task data"""

    data_source: str = ""
    data_type: str = ""
    processing_type: str = ""  # clean, transform, analyze, etc.
    output_format: Optional[str] = None


@dataclass
class MonitoringTask:
    """System monitoring task data"""

    system_name: str = ""
    metric_type: str = ""
    threshold: Optional[float] = None
    alert_config: Optional[Dict[str, Any]] = None


class OperationsService:
    """
    Operations domain service.

    Provides operations-specific task creation and management
    built on top of BusinessService.
    """

    def __init__(self, business_service: BusinessService):
        """Initialize operations service"""
        self.business = business_service
        logger.info("operations_service_initialized")

    async def create_automation_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        process_name: str,
        automation_type: str,
        frequency: Optional[str] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create process automation task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            process_name: Name of the process to automate
            automation_type: Type of automation
            frequency: Optional frequency (once, daily, weekly, etc.)
            priority: Task priority

        Returns:
            Created business task
        """
        automation_data = AutomationTask(
            process_name=process_name,
            automation_type=automation_type,
            frequency=frequency,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.OPERATIONS,
            title=title,
            description=description,
            priority=priority,
            context={"automation": automation_data.__dict__},
            tags=["automation", automation_type, process_name],
        )

        logger.info(
            f"Automation task created: {title}",
            extra={
                "task_id": str(task.id),
                "process": process_name,
                "type": automation_type,
            },
        )

        return task

    async def create_data_processing_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        data_source: str,
        data_type: str,
        processing_type: str,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    ) -> BusinessTask:
        """
        Create data processing task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            data_source: Source of the data
            data_type: Type of data
            processing_type: Type of processing (clean, transform, analyze, etc.)
            priority: Task priority

        Returns:
            Created business task
        """
        data_task = DataProcessingTask(
            data_source=data_source,
            data_type=data_type,
            processing_type=processing_type,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.OPERATIONS,
            title=title,
            description=description,
            priority=priority,
            context={"data_processing": data_task.__dict__},
            tags=["data", processing_type, data_type],
        )

        logger.info(
            f"Data processing task created: {title}",
            extra={
                "task_id": str(task.id),
                "source": data_source,
                "processing": processing_type,
            },
        )

        return task

    async def create_monitoring_task(
        self,
        user_id: UUID,
        title: str,
        description: str,
        system_name: str,
        metric_type: str,
        threshold: Optional[float] = None,
        priority: BusinessTaskPriority = BusinessTaskPriority.HIGH,
    ) -> BusinessTask:
        """
        Create system monitoring task.

        Args:
            user_id: User creating the task
            title: Task title
            description: Task description
            system_name: Name of the system to monitor
            metric_type: Type of metric
            threshold: Optional threshold value
            priority: Task priority

        Returns:
            Created business task
        """
        monitoring_data = MonitoringTask(
            system_name=system_name,
            metric_type=metric_type,
            threshold=threshold,
        )

        task = await self.business.create_task(
            user_id=user_id,
            domain=BusinessDomain.OPERATIONS,
            title=title,
            description=description,
            priority=priority,
            context={"monitoring": monitoring_data.__dict__},
            tags=["monitoring", system_name, metric_type],
        )

        logger.info(
            f"Monitoring task created: {title}",
            extra={
                "task_id": str(task.id),
                "system": system_name,
                "metric": metric_type,
            },
        )

        return task
