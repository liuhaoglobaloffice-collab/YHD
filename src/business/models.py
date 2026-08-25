"""
Business OS - Data Models

Defines business-level task and domain models that integrate with:
- AI Employees (workforce)
- Workflows
- Tasks
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class BusinessDomain(str, Enum):
    """Business domains in the enterprise"""

    MARKETING = "marketing"
    SALES = "sales"
    OPERATIONS = "operations"
    RESEARCH = "research"
    GENERAL = "general"


class BusinessTaskStatus(str, Enum):
    """Business task status"""

    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BusinessTaskPriority(str, Enum):
    """Business task priority"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BusinessTask:
    """
    Business-level task that can be assigned to AI Employees
    and executed through Workflows.

    This is a higher-level abstraction than Task (Stage 5).
    A BusinessTask may spawn multiple Tasks and Workflows.
    """

    id: UUID = field(default_factory=uuid4)
    domain: BusinessDomain = BusinessDomain.GENERAL
    title: str = ""
    description: str = ""
    priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM
    status: BusinessTaskStatus = BusinessTaskStatus.CREATED

    # Assignment
    assigned_employee_id: Optional[UUID] = None
    assigned_by: Optional[UUID] = None  # User ID
    assigned_at: Optional[datetime] = None

    # Execution
    workflow_id: Optional[UUID] = None
    task_ids: List[UUID] = field(default_factory=list)

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None

    # Business context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "domain": self.domain.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_employee_id": (
                str(self.assigned_employee_id) if self.assigned_employee_id else None
            ),
            "assigned_by": str(self.assigned_by) if self.assigned_by else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "task_ids": [str(tid) for tid in self.task_ids],
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context,
            "tags": self.tags,
        }


@dataclass
class BusinessMetrics:
    """Business metrics for a domain or employee"""

    domain: BusinessDomain
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    in_progress_tasks: int = 0
    avg_completion_time_seconds: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "domain": self.domain.value,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "avg_completion_time_seconds": self.avg_completion_time_seconds,
            "success_rate": self.success_rate,
        }
