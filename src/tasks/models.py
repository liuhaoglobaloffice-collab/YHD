"""
Task Models - Stage 5
Task data models and enums
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"  # Waiting for dependencies


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Task types"""

    GENERAL = "general"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CODING = "coding"
    REVIEW = "review"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    SALES = "sales"
    MARKETING = "marketing"
    CUSTOMER_SERVICE = "customer_service"
    CONTENT_CREATION = "content_creation"
    DATA_PROCESSING = "data_processing"
    REPORTING = "reporting"
    PLANNING = "planning"
    DECISION = "decision"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class TaskDependency:
    """Task dependency"""

    task_id: UUID
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, finish_to_finish

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "dependency_type": self.dependency_type,
        }


@dataclass
class TaskResult:
    """Task execution result"""

    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat(),
        }


@dataclass
class Task:
    """
    Task entity

    Represents a unit of work that can be executed by agents or systems.
    Tasks can have dependencies, priorities, and belong to workflows.
    """

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    task_type: TaskType = TaskType.OTHER
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    # Assignment
    assigned_to: List[UUID] = field(default_factory=list)  # Agent IDs
    creator_id: Optional[UUID] = None

    # Relationships
    workflow_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    dependencies: List[TaskDependency] = field(default_factory=list)

    # Execution
    input_data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[TaskResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # Audit
    trace_id: UUID = field(default_factory=uuid4)

    def is_ready(self, completed_tasks: set[UUID]) -> bool:
        """
        Check if task is ready to execute

        Args:
            completed_tasks: Set of completed task IDs

        Returns:
            True if all dependencies are satisfied
        """
        if self.status != TaskStatus.PENDING:
            return False

        # Check dependencies
        for dep in self.dependencies:
            if dep.task_id not in completed_tasks:
                return False

        return True

    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def mark_running(self) -> None:
        """Mark task as running"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(UTC)
        logger.info("task_started", task_id=self.id, title=self.title)

    def mark_completed(self, result: TaskResult) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(UTC)
        logger.info("task_completed", task_id=self.id, title=self.title)

    def mark_failed(self, error: str) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.result = TaskResult(success=False, error=error)
        self.completed_at = datetime.now(UTC)
        logger.error("task_failed", task_id=self.id, title=self.title, error=error)

    def mark_cancelled(self) -> None:
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(UTC)
        logger.info("task_cancelled", task_id=self.id, title=self.title)

    def mark_blocked(self) -> None:
        """Mark task as blocked"""
        self.status = TaskStatus.BLOCKED
        logger.info("task_blocked", task_id=self.id, title=self.title)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_to": [str(a) for a in self.assigned_to],
            "creator_id": str(self.creator_id) if self.creator_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "input_data": self.input_data,
            "result": self.result.to_dict() if self.result else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "trace_id": str(self.trace_id),
        }
