"""
AI Brain Models - Data models for CEO commands and brain operations.

Part of Phase 3.1 AI Brain Core.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class CommandStatus(str, Enum):
    """CEO command execution status."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandPriority(str, Enum):
    """Command priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CEOCommand:
    """
    CEO Command record.

    Represents a natural language command from CEO that needs to be
    decomposed into executable tasks.
    """

    command_id: UUID
    command_text: str
    user_id: UUID
    goal: str
    priority: CommandPriority
    status: CommandStatus
    task_plan_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.priority, str):
            self.priority = CommandPriority(self.priority)
        if isinstance(self.status, str):
            self.status = CommandStatus(self.status)


@dataclass
class ParsedCommand:
    """
    Parsed CEO command with extracted goal and constraints.

    Result of natural language processing on CEO command.

    P0-1: KPI / budget / time / risk fields are extracted by the LLM
    parser when a real Provider is configured; the rule-based parser
    leaves them None (boss must fill them manually).
    """

    goal: str
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: CommandPriority = CommandPriority.NORMAL
    estimated_complexity: str = "medium"  # low, medium, high
    required_agents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # P0-1 LLM 目标理解提取的经营要素（None = 未提取到）
    kpi_name: Optional[str] = None
    kpi_target: Optional[float] = None
    kpi_unit: Optional[str] = None
    budget_total: Optional[float] = None
    time_start: Optional[str] = None  # ISO 日期字符串
    time_end: Optional[str] = None  # ISO 日期字符串
    risk_boundaries: List[str] = field(default_factory=list)


@dataclass
class TaskDecomposition:
    """
    Decomposed task plan from goal.

    Represents breakdown of high-level goal into executable tasks.
    """

    goal: str
    tasks: List[Dict[str, Any]]
    execution_order: str = "sequential"  # sequential, parallel, hybrid
    estimated_duration_minutes: Optional[int] = None
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAssignment:
    """
    Assignment of task to specific AI agent/employee.
    """

    task_id: UUID
    task_description: str
    agent_type: str
    employee_id: Optional[UUID] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    confidence: float = 1.0
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
