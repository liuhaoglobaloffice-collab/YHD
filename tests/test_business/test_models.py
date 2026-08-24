"""
Tests for Business models
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.business.models import (
    BusinessDomain,
    BusinessMetrics,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)


def test_business_task_creation():
    """Test business task creation"""
    task = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Test Task",
        description="Test Description",
        priority=BusinessTaskPriority.HIGH,
    )

    assert task.id is not None
    assert task.domain == BusinessDomain.MARKETING
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.priority == BusinessTaskPriority.HIGH
    assert task.status == BusinessTaskStatus.CREATED
    assert task.assigned_employee_id is None
    assert task.workflow_id is None
    assert task.task_ids == []
    assert task.result is None
    assert task.error is None
    assert task.context == {}
    assert task.tags == []


def test_business_task_to_dict():
    """Test task serialization"""
    task = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Test",
        description="Description",
        priority=BusinessTaskPriority.URGENT,
        tags=["tag1", "tag2"],
    )

    data = task.to_dict()

    assert data["domain"] == "sales"
    assert data["title"] == "Test"
    assert data["priority"] == "urgent"
    assert data["status"] == "created"
    assert data["tags"] == ["tag1", "tag2"]


def test_business_task_with_assignment():
    """Test task with assignment"""
    employee_id = uuid4()
    user_id = uuid4()

    task = BusinessTask(
        domain=BusinessDomain.OPERATIONS,
        title="Assigned Task",
        description="Description",
        assigned_employee_id=employee_id,
        assigned_by=user_id,
        assigned_at=datetime.now(UTC),
        status=BusinessTaskStatus.ASSIGNED,
    )

    assert task.assigned_employee_id == employee_id
    assert task.assigned_by == user_id
    assert task.assigned_at is not None
    assert task.status == BusinessTaskStatus.ASSIGNED


def test_business_metrics_creation():
    """Test business metrics creation"""
    metrics = BusinessMetrics(
        domain=BusinessDomain.RESEARCH,
        total_tasks=100,
        completed_tasks=75,
        failed_tasks=10,
        in_progress_tasks=15,
        avg_completion_time_seconds=3600.0,
        success_rate=0.88,
    )

    assert metrics.domain == BusinessDomain.RESEARCH
    assert metrics.total_tasks == 100
    assert metrics.completed_tasks == 75
    assert metrics.failed_tasks == 10
    assert metrics.in_progress_tasks == 15
    assert metrics.avg_completion_time_seconds == 3600.0
    assert abs(metrics.success_rate - 0.88) < 0.01


def test_business_metrics_to_dict():
    """Test metrics serialization"""
    metrics = BusinessMetrics(
        domain=BusinessDomain.MARKETING,
        total_tasks=50,
        success_rate=0.9,
    )

    data = metrics.to_dict()

    assert data["domain"] == "marketing"
    assert data["total_tasks"] == 50
    assert abs(data["success_rate"] - 0.9) < 0.01


def test_business_domain_enum():
    """Test business domain enum values"""
    assert BusinessDomain.MARKETING.value == "marketing"
    assert BusinessDomain.SALES.value == "sales"
    assert BusinessDomain.OPERATIONS.value == "operations"
    assert BusinessDomain.RESEARCH.value == "research"
    assert BusinessDomain.GENERAL.value == "general"


def test_business_task_status_enum():
    """Test business task status enum values"""
    assert BusinessTaskStatus.CREATED.value == "created"
    assert BusinessTaskStatus.ASSIGNED.value == "assigned"
    assert BusinessTaskStatus.IN_PROGRESS.value == "in_progress"
    assert BusinessTaskStatus.REVIEW.value == "review"
    assert BusinessTaskStatus.COMPLETED.value == "completed"
    assert BusinessTaskStatus.FAILED.value == "failed"
    assert BusinessTaskStatus.CANCELLED.value == "cancelled"


def test_business_task_priority_enum():
    """Test business task priority enum values"""
    assert BusinessTaskPriority.LOW.value == "low"
    assert BusinessTaskPriority.MEDIUM.value == "medium"
    assert BusinessTaskPriority.HIGH.value == "high"
    assert BusinessTaskPriority.URGENT.value == "urgent"
