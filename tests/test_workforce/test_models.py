"""
Tests for AI Employee models and data structures.
"""

from uuid import uuid4

from src.ai.agents import AgentType
from src.workforce.models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    EmployeeCostRecord,
    EmployeePerformanceRecord,
    Position,
)


def test_ai_employee_creation():
    """Test creating an AI employee."""
    employee = AIEmployee(
        name="Marketing AI - Sarah",
        department=Department.MARKETING,
        position=Position.MARKETING_SPECIALIST,
        description="Marketing specialist focused on SEO and content",
        agent_type=AgentType.GPT,
    )

    assert employee.id is not None
    assert employee.name == "Marketing AI - Sarah"
    assert employee.department == Department.MARKETING
    assert employee.position == Position.MARKETING_SPECIALIST
    assert employee.status == AIEmployeeStatus.CREATED
    assert employee.agent_type == AgentType.GPT
    assert employee.tasks_completed == 0
    assert employee.tasks_failed == 0


def test_ai_employee_to_dict():
    """Test converting employee to dictionary."""
    employee = AIEmployee(
        name="Sales AI - John",
        department=Department.SALES,
        position=Position.SALES_REPRESENTATIVE,
        description="Sales representative for customer outreach",
        agent_type=AgentType.CLAUDE,
        status=AIEmployeeStatus.ACTIVE,
    )

    data = employee.to_dict()

    assert data["name"] == "Sales AI - John"
    assert data["department"] == "sales"
    assert data["position"] == "sales_representative"
    assert data["status"] == "active"
    assert data["agent_type"] == "claude"
    assert isinstance(data["id"], str)


def test_employee_performance_record():
    """Test creating performance record."""
    employee_id = uuid4()
    task_id = uuid4()

    record = EmployeePerformanceRecord(
        employee_id=employee_id,
        task_id=task_id,
        success=True,
        execution_time_seconds=10.5,
        cost_usd=0.05,
        user_rating=4,
        quality_score=0.85,
    )

    assert record.employee_id == employee_id
    assert record.task_id == task_id
    assert record.success is True
    assert record.execution_time_seconds == 10.5
    assert record.cost_usd == 0.05
    assert record.user_rating == 4
    assert record.quality_score == 0.85


def test_employee_cost_record():
    """Test creating cost record."""
    employee_id = uuid4()
    task_id = uuid4()

    record = EmployeeCostRecord(
        employee_id=employee_id,
        task_id=task_id,
        provider="openai",
        model_id="gpt-4",
        input_tokens=100,
        output_tokens=50,
        input_cost_usd=0.003,
        output_cost_usd=0.006,
    )

    assert record.employee_id == employee_id
    assert record.task_id == task_id
    assert record.provider == "openai"
    assert record.model_id == "gpt-4"
    assert record.input_tokens == 100
    assert record.output_tokens == 50
    assert record.total_tokens == 150
    assert record.input_cost_usd == 0.003
    assert record.output_cost_usd == 0.006
    assert abs(record.total_cost_usd - 0.009) < 0.0001


def test_department_enum():
    """Test department enum values."""
    assert Department.CEO_OFFICE.value == "ceo_office"
    assert Department.MARKETING.value == "marketing"
    assert Department.SALES.value == "sales"
    assert Department.RESEARCH.value == "research"
    assert Department.OPERATIONS.value == "operations"


def test_position_enum():
    """Test position enum values."""
    assert Position.CEO_ASSISTANT.value == "ceo_assistant"
    assert Position.MARKETING_SPECIALIST.value == "marketing_specialist"
    assert Position.SALES_REPRESENTATIVE.value == "sales_representative"
    assert Position.MARKET_RESEARCHER.value == "market_researcher"


def test_employee_status_enum():
    """Test employee status enum values."""
    assert AIEmployeeStatus.CREATED.value == "created"
    assert AIEmployeeStatus.TRAINING.value == "training"
    assert AIEmployeeStatus.ACTIVE.value == "active"
    assert AIEmployeeStatus.SUSPENDED.value == "suspended"
    assert AIEmployeeStatus.RETIRED.value == "retired"
