"""
AI Employee Data Models.

Stage 6: AI Employee Identity System
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from ..ai.agents import AgentType


class AIEmployeeStatus(str, Enum):
    """AI Employee lifecycle status."""

    CREATED = "created"  # Employee created, not yet configured
    TRAINING = "training"  # Under configuration/onboarding
    ACTIVE = "active"  # Actively working
    SUSPENDED = "suspended"  # Temporarily disabled
    RETIRED = "retired"  # Permanently disabled


class Department(str, Enum):
    """AI Employee departments."""

    CEO_OFFICE = "ceo_office"  # CEO Office - Strategic AI
    MARKETING = "marketing"  # Marketing Department
    SALES = "sales"  # Sales Department
    RESEARCH = "research"  # Research Department
    OPERATIONS = "operations"  # Operations Department
    ENGINEERING = "engineering"  # Engineering/Tech Department
    ANALYTICS = "analytics"  # Data Analytics Department


class Position(str, Enum):
    """AI Employee positions."""

    # CEO Office
    CEO_ASSISTANT = "ceo_assistant"  # AI CEO Assistant
    STRATEGY_ANALYST = "strategy_analyst"  # Strategy Analyst

    # Marketing
    MARKETING_SPECIALIST = "marketing_specialist"  # Marketing Specialist
    SEO_SPECIALIST = "seo_specialist"  # SEO Specialist
    CONTENT_WRITER = "content_writer"  # Content Writer

    # Sales
    SALES_REPRESENTATIVE = "sales_representative"  # Sales Representative
    ACCOUNT_MANAGER = "account_manager"  # Account Manager
    CUSTOMER_SUCCESS = "customer_success"  # Customer Success Manager

    # Research
    MARKET_RESEARCHER = "market_researcher"  # Market Researcher
    COMPETITIVE_ANALYST = "competitive_analyst"  # Competitive Analyst
    PRODUCT_RESEARCHER = "product_researcher"  # Product Researcher

    # Operations
    OPERATIONS_COORDINATOR = "operations_coordinator"  # Operations Coordinator
    DATA_PROCESSOR = "data_processor"  # Data Processor
    TASK_MANAGER = "task_manager"  # Task Manager

    # Engineering
    SYSTEM_ENGINEER = "system_engineer"  # System Engineer
    INTEGRATION_SPECIALIST = "integration_specialist"  # Integration Specialist

    # Analytics
    DATA_ANALYST = "data_analyst"  # Data Analyst
    BUSINESS_ANALYST = "business_analyst"  # Business Analyst


@dataclass
class AIEmployee:
    """
    AI Employee - Business entity representing an AI workforce member.

    Architecture:
        AIEmployee (Business Layer) → Agent Runtime → Provider

    AI Employee ≠ Agent:
        - Employee: Business identity (name, department, position, permissions)
        - Agent: Runtime execution (AgentType, provider, tools)

    One employee can use multiple agents depending on task requirements.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""  # Employee name (e.g., "Marketing AI - Sarah")
    department: Department = Department.OPERATIONS
    position: Position = Position.TASK_MANAGER
    description: str = ""  # Role description and responsibilities

    # Agent Runtime Configuration
    agent_type: Optional[AgentType] = None  # Assigned AI agent
    provider_config: Dict[str, Any] = field(default_factory=dict)  # Provider-specific settings

    # Lifecycle
    status: AIEmployeeStatus = AIEmployeeStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None

    # Permissions (RBAC integration)
    role_ids: list[UUID] = field(default_factory=list)  # Assigned RBAC roles
    permission_overrides: Dict[str, bool] = field(default_factory=dict)  # Permission overrides

    # Performance Tracking
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time_seconds: float = 0.0
    total_cost_usd: float = 0.0

    # Metadata
    owner_id: Optional[UUID] = None  # User who created/manages this employee
    team_ids: list[UUID] = field(default_factory=list)  # Team memberships
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "department": self.department.value,
            "position": self.position.value,
            "description": self.description,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "retired_at": self.retired_at.isoformat() if self.retired_at else None,
            "role_ids": [str(r) for r in self.role_ids],
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_execution_time_seconds": self.total_execution_time_seconds,
            "total_cost_usd": self.total_cost_usd,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "team_ids": [str(t) for t in self.team_ids],
            "metadata": self.metadata,
        }


@dataclass
class EmployeePerformanceRecord:
    """Performance record for an AI employee."""

    id: UUID = field(default_factory=uuid4)
    employee_id: UUID = field(default_factory=uuid4)

    # Performance Metrics
    task_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    success: bool = False
    execution_time_seconds: float = 0.0
    cost_usd: float = 0.0

    # Quality Metrics
    user_rating: Optional[int] = None  # 1-5 stars
    quality_score: Optional[float] = None  # 0.0-1.0
    error_message: Optional[str] = None

    # Timestamps
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmployeeCostRecord:
    """Cost tracking record for an AI employee."""

    id: UUID = field(default_factory=uuid4)
    employee_id: UUID = field(default_factory=uuid4)

    # Cost Breakdown
    task_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    provider: str = ""  # Provider name (e.g., "openai", "anthropic")
    model_id: str = ""  # Model used

    # Token Usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Cost (USD)
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

    # Timestamps
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate totals if not provided."""
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
        if self.total_cost_usd == 0.0:
            self.total_cost_usd = self.input_cost_usd + self.output_cost_usd
