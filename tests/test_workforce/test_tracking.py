"""
Tests for Performance and Cost Trackers.
"""

from uuid import uuid4

import pytest

from src.ai.agents import AgentType
from src.workforce.cost import CostTracker
from src.workforce.models import AIEmployee, Department, Position
from src.workforce.performance import PerformanceTracker
from src.workforce.registry import AIEmployeeRegistry


@pytest.fixture
def registry(async_session):
    """Create registry."""
    return AIEmployeeRegistry(async_session)


@pytest.fixture
async def employee(registry):
    """Create and register a sample employee."""
    emp = AIEmployee(
        name="Test Employee",
        department=Department.OPERATIONS,
        position=Position.TASK_MANAGER,
        description="Test",
        agent_type=AgentType.GPT,
    )
    return await registry.register(emp)


@pytest.fixture
def perf_tracker(registry):
    """Create performance tracker."""
    return PerformanceTracker(registry)


@pytest.fixture
def cost_tracker(registry):
    """Create cost tracker."""
    return CostTracker(registry)


async def test_record_performance(perf_tracker, employee):
    """Test recording performance."""
    task_id = uuid4()

    record = await perf_tracker.record_performance(
        employee_id=employee.id,
        task_id=task_id,
        success=True,
        execution_time_seconds=10.0,
        cost_usd=0.05,
        user_rating=5,
        quality_score=0.9,
    )

    assert record.employee_id == employee.id
    assert record.task_id == task_id
    assert record.success is True
    assert record.execution_time_seconds == 10.0


async def test_performance_updates_employee_stats(perf_tracker, employee, registry):
    """Test performance tracking updates employee stats."""
    await perf_tracker.record_performance(
        employee_id=employee.id,
        success=True,
        execution_time_seconds=10.0,
        cost_usd=0.05,
    )

    updated = await registry.get(employee.id)
    assert updated.tasks_completed == 1
    assert updated.total_execution_time_seconds == 10.0
    assert updated.total_cost_usd == 0.05


async def test_performance_summary(perf_tracker, employee):
    """Test getting performance summary."""
    await perf_tracker.record_performance(
        employee_id=employee.id,
        success=True,
        execution_time_seconds=10.0,
        cost_usd=0.05,
        user_rating=4,
    )
    await perf_tracker.record_performance(
        employee_id=employee.id,
        success=False,
        execution_time_seconds=5.0,
        cost_usd=0.02,
    )

    summary = await perf_tracker.get_performance_summary(employee.id)

    assert summary["total_tasks"] == 2
    assert summary["tasks_completed"] == 1
    assert summary["tasks_failed"] == 1
    assert summary["success_rate"] == 0.5
    assert summary["average_user_rating"] == 4.0


async def test_record_cost(cost_tracker, employee):
    """Test recording cost."""
    task_id = uuid4()

    record = await cost_tracker.record_cost(
        employee_id=employee.id,
        provider="openai",
        model_id="gpt-4",
        input_tokens=100,
        output_tokens=50,
        input_cost_usd=0.003,
        output_cost_usd=0.006,
        task_id=task_id,
    )

    assert record.employee_id == employee.id
    assert record.provider == "openai"
    assert record.total_tokens == 150
    assert abs(record.total_cost_usd - 0.009) < 0.0001


async def test_cost_summary(cost_tracker, employee):
    """Test getting cost summary."""
    await cost_tracker.record_cost(
        employee_id=employee.id,
        provider="openai",
        model_id="gpt-4",
        input_tokens=100,
        output_tokens=50,
        input_cost_usd=0.003,
        output_cost_usd=0.006,
    )
    await cost_tracker.record_cost(
        employee_id=employee.id,
        provider="anthropic",
        model_id="claude-3",
        input_tokens=200,
        output_tokens=100,
        input_cost_usd=0.004,
        output_cost_usd=0.008,
    )

    summary = await cost_tracker.get_cost_summary(employee.id)

    assert summary["total_tokens"] == 450
    assert summary["total_cost_usd"] == 0.021
    assert "openai" in summary["provider_breakdown"]
    assert "anthropic" in summary["provider_breakdown"]


async def test_total_system_cost(cost_tracker, registry):
    """Test getting total system cost."""
    emp1 = AIEmployee(
        name="Employee 1",
        department=Department.MARKETING,
        position=Position.MARKETING_SPECIALIST,
        description="Test",
        agent_type=AgentType.GPT,
    )
    emp2 = AIEmployee(
        name="Employee 2",
        department=Department.SALES,
        position=Position.SALES_REPRESENTATIVE,
        description="Test",
        agent_type=AgentType.GPT,
    )

    await registry.register(emp1)
    await registry.register(emp2)

    await cost_tracker.record_cost(
        employee_id=emp1.id,
        provider="openai",
        model_id="gpt-4",
        input_tokens=100,
        output_tokens=50,
        input_cost_usd=0.003,
        output_cost_usd=0.006,
    )
    await cost_tracker.record_cost(
        employee_id=emp2.id,
        provider="openai",
        model_id="gpt-4",
        input_tokens=200,
        output_tokens=100,
        input_cost_usd=0.006,
        output_cost_usd=0.012,
    )

    summary = await cost_tracker.get_total_system_cost()

    assert summary["total_employees"] == 2
    assert summary["total_tokens"] == 450
    assert abs(summary["total_cost_usd"] - 0.027) < 0.0001
