"""
Database Models - SQLAlchemy ORM Models

Defines database schema for Stage 4-7 entities.

Note: Models from other modules (identity, supplier)
are imported by their respective __init__.py files to avoid circular imports.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base

# =============================================================================
# Stage 4: Knowledge + Company Brain
# =============================================================================


class DocumentModel(Base):
    """
    Document storage model.

    Stores uploaded documents and their metadata.
    """

    __tablename__ = "documents"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Document Info
    filename = Column(String(255), nullable=False)
    title = Column(String(500))
    file_type = Column(String(50), nullable=False)  # pdf, docx, xlsx, markdown
    size = Column(Integer, nullable=False)  # bytes

    # Content
    content = Column(Text)  # Extracted text content
    summary = Column(Text)  # AI-generated summary

    # Embedding
    embedding = Column(JSON)  # Vector embedding for semantic search

    # Metadata
    tags = Column(JSON)  # List[str]
    meta = Column(JSON)  # Dict[str, Any]

    # Ownership
    created_by = Column(String(36), nullable=False)  # User ID
    company_id = Column(String(36))  # Company ID (optional)

    # Status
    status = Column(String(50), nullable=False)  # uploaded, processing, indexed, available

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_documents_created_by", "created_by"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_file_type", "file_type"),
        Index("idx_documents_created_at", "created_at"),
    )

    chunks = relationship("DocumentChunkModel", back_populates="document")
    embeddings = relationship("EmbeddingStorageModel", back_populates="document")


class DocumentChunkModel(Base):
    """Phase 2.2 document chunk persistence model.

    Stores individual text chunks extracted from a document and keeps the
    metadata payload in a structured JSON field for future retrieval/search.
    """

    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("DocumentModel", back_populates="chunks")


class EmbeddingStorageModel(Base):
    """Phase 2.2 lightweight embedding record model.

    Stores vector metadata and provider identifier in a future-friendly
    shape separate from the document payload itself.
    """

    __tablename__ = "embedding_storage"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    chunk_id = Column(String(36), nullable=True)
    vector = Column(JSON, nullable=False)
    dimension = Column(Integer, nullable=False, default=3)
    provider = Column(String(80), nullable=False, default="mock")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("DocumentModel", back_populates="embeddings")


class MemoryModel(Base):
    """
    Long-term memory storage for AI agents.

    Stores persistent memories for agents and users.
    """

    __tablename__ = "memories"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Ownership
    agent_id = Column(String(36))  # AI Agent ID (optional)
    user_id = Column(String(36))  # User ID (optional)
    company_id = Column(String(36))  # Company ID (optional)

    # Memory Content
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), nullable=False)  # episodic, semantic, procedural

    # Importance
    importance = Column(Float, default=1.0)  # 0.0 - 1.0

    # Embedding
    embedding = Column(JSON)  # Vector embedding for retrieval

    # Context
    context = Column(JSON)  # Dict[str, Any] - additional context
    tags = Column(JSON)  # List[str]

    # Session and Task tracking
    session_id = Column(String(255))  # For short-term memory
    task_id = Column(String(255))  # For working memory

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed_at = Column(DateTime)
    access_count = Column(Integer, default=0)
    expires_at = Column(DateTime)  # For short-term and working memory expiration

    # Indexes
    __table_args__ = (
        Index("idx_memories_agent_id", "agent_id"),
        Index("idx_memories_user_id", "user_id"),
        Index("idx_memories_memory_type", "memory_type"),
        Index("idx_memories_importance", "importance"),
    )


class CompanyBrainEntityModel(Base):
    """
    Company knowledge graph entity.

    Represents entities in company knowledge graph (people, products, processes, etc.).
    """

    __tablename__ = "company_brain_entities"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Entity Info
    name = Column(String(500), nullable=False)
    entity_type = Column(String(100), nullable=False)  # person, product, process, concept, etc.
    description = Column(Text)

    # Attributes
    attributes = Column(JSON)  # Dict[str, Any]

    # Relationships (stored as adjacency list)
    relationships = Column(JSON)  # List[{"target_id": str, "type": str, "weight": float}]

    # Embedding
    embedding = Column(JSON)  # Vector embedding

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Ownership
    company_id = Column(String(36), nullable=False)
    created_by = Column(String(36), nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_company_brain_entity_type", "entity_type"),
        Index("idx_company_brain_company_id", "company_id"),
        Index("idx_company_brain_name", "name"),
    )


class CompanyBrainFactModel(Base):
    """
    Company Brain Fact

    Facts about entities in the company knowledge graph.
    """

    __tablename__ = "company_brain_facts"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Entity relationship
    entity_id = Column(String(36), nullable=False)

    # Fact content
    attribute = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)  # Can be any JSON-serializable value

    # Source tracking
    source = Column(String(500), nullable=False)
    source_document_id = Column(String(36))
    source_document_version = Column(Integer)

    # Confidence and priority
    confidence = Column(
        String(50), nullable=False
    )  # verified, high, medium, low, inferred, unknown
    priority = Column(Integer, nullable=False)  # 10-100 (higher = more authoritative)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Conflict tracking
    supersedes = Column(String(36))  # Fact ID that this fact supersedes
    superseded_by = Column(String(36))  # Fact ID that supersedes this fact

    # Ownership
    company_id = Column(String(36), nullable=False)
    created_by = Column(String(36))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_company_brain_facts_entity_id", "entity_id"),
        Index("idx_company_brain_facts_attribute", "attribute"),
        Index("idx_company_brain_facts_company_id", "company_id"),
        Index("idx_company_brain_facts_active", "is_active"),
    )


# =============================================================================
# Stage 5: Workflow + Execution
# =============================================================================


class WorkflowModel(Base):
    """
    Workflow definition model.

    Stores workflow definitions (templates).
    """

    __tablename__ = "workflows"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Workflow Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(Integer, nullable=False, default=1)

    # Definition
    steps = Column(JSON, nullable=False)  # List[WorkflowStep] serialized

    # Status
    enabled = Column(Boolean, nullable=False, default=True)

    # Context
    context = Column(JSON)  # Dict[str, Any] - metadata, permissions, etc.
    tags = Column(JSON)  # List[str]

    # Ownership
    created_by = Column(String(36), nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = relationship(
        "WorkflowExecutionModel", back_populates="workflow", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_workflows_created_by", "created_by"),
        Index("idx_workflows_enabled", "enabled"),
        Index("idx_workflows_name", "name"),
    )


class WorkflowExecutionModel(Base):
    """
    Workflow execution instance model.

    Tracks individual workflow executions.
    """

    __tablename__ = "workflow_executions"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Foreign Key
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)

    # Execution Info
    user_id = Column(String(36), nullable=False)
    status = Column(String(50), nullable=False)  # pending, running, completed, failed, cancelled

    # Data
    variables = Column(JSON)  # Dict[str, Any] - execution variables
    result = Column(JSON)  # Dict[str, Any] - execution result
    error = Column(Text)  # Error message if failed

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    workflow = relationship("WorkflowModel", back_populates="executions")

    # Indexes
    __table_args__ = (
        Index("idx_workflow_executions_workflow_id", "workflow_id"),
        Index("idx_workflow_executions_user_id", "user_id"),
        Index("idx_workflow_executions_status", "status"),
    )


class TaskModel(Base):
    """
    Task model.

    Represents individual tasks in the system.
    """

    __tablename__ = "tasks"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Task Info
    title = Column(String(500), nullable=False)
    description = Column(Text)
    task_type = Column(String(100), nullable=False)  # ai_inference, web_search, data_analysis, etc.

    # Status
    status = Column(
        String(50), nullable=False
    )  # pending, running, completed, failed, blocked, cancelled
    priority = Column(String(50), nullable=False)  # critical, urgent, high, medium, low

    # Assignment
    assigned_to = Column(JSON)  # List[str] - Agent IDs
    creator_id = Column(String(36), nullable=False)

    # Relationships
    workflow_id = Column(String(36))  # Optional workflow ID
    parent_task_id = Column(String(36))  # Optional parent task

    # Dependencies
    dependencies = Column(JSON)  # List[{"task_id": str, "type": str}]

    # Data
    input_data = Column(JSON)  # Dict[str, Any]
    result_data = Column(JSON)  # Dict[str, Any]
    error = Column(Text)

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    deadline = Column(DateTime)

    # Indexes
    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_workflow_id", "workflow_id"),
        Index("idx_tasks_creator_id", "creator_id"),
        Index("idx_tasks_task_type", "task_type"),
    )


class TaskResultModel(Base):
    """
    Task result model.

    Stores historical task execution results.
    """

    __tablename__ = "task_results"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Foreign Key
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)

    # Result
    success = Column(Boolean, nullable=False)
    output = Column(JSON)  # Dict[str, Any]
    error = Column(Text)

    # Metrics
    execution_time_seconds = Column(Float)

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_task_results_task_id", "task_id"),
        Index("idx_task_results_success", "success"),
    )


# =============================================================================
# Stage 6: AI Workforce
# =============================================================================


class AIEmployeeModel(Base):
    """
    AI Employee model.

    Represents AI employees in the workforce.
    """

    __tablename__ = "ai_employees"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Employee Info
    name = Column(String(255), nullable=False, unique=True)
    department = Column(String(100), nullable=False)  # ceo_office, marketing, sales, etc.
    position = Column(String(100), nullable=False)  # ceo_assistant, marketing_ai, etc.
    description = Column(Text)

    # Configuration
    agent_type = Column(String(100), nullable=True)  # conversational, analytical, creative, etc.
    provider = Column(String(100))  # openai, anthropic, google, etc.
    model = Column(String(100))  # gpt-4, claude-3, etc.
    config = Column(JSON)  # Dict[str, Any] - model config

    # Capabilities
    capabilities = Column(JSON)  # List[str]

    # Status
    status = Column(String(50), nullable=False)  # created, training, active, suspended, retired

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    performance_records = relationship(
        "EmployeePerformanceModel", back_populates="employee", cascade="all, delete-orphan"
    )
    cost_records = relationship(
        "EmployeeCostModel", back_populates="employee", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_ai_employees_status", "status"),
        Index("idx_ai_employees_department", "department"),
        Index("idx_ai_employees_position", "position"),
    )


class EmployeePerformanceModel(Base):
    """
    AI Employee performance tracking model.

    Records performance metrics for AI employees.
    """

    __tablename__ = "employee_performance"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Foreign Key
    employee_id = Column(String(36), ForeignKey("ai_employees.id"), nullable=False)

    # Metrics
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    avg_execution_time_seconds = Column(Float)
    success_rate = Column(Float)  # 0.0 - 1.0

    # User Feedback
    user_rating = Column(Float)  # 0.0 - 5.0

    # Time Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    employee = relationship("AIEmployeeModel", back_populates="performance_records")

    # Indexes
    __table_args__ = (
        Index("idx_employee_performance_employee_id", "employee_id"),
        Index("idx_employee_performance_period", "period_start", "period_end"),
    )


class EmployeeCostModel(Base):
    """
    AI Employee cost tracking model.

    Records API costs for AI employees.
    """

    __tablename__ = "employee_costs"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Foreign Key
    employee_id = Column(String(36), ForeignKey("ai_employees.id"), nullable=False)

    # Cost Metrics
    api_calls = Column(Integer, nullable=False, default=0)
    tokens_used = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)

    # Time Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    employee = relationship("AIEmployeeModel", back_populates="cost_records")

    # Indexes
    __table_args__ = (
        Index("idx_employee_costs_employee_id", "employee_id"),
        Index("idx_employee_costs_period", "period_start", "period_end"),
    )


# =============================================================================
# Stage 7: Business OS
# =============================================================================


class BusinessTaskModel(Base):
    """
    Business task model.

    Represents business-level tasks (Sales, Marketing, SEO, etc.).
    """

    __tablename__ = "business_tasks"

    # Primary Key
    id = Column(String(36), primary_key=True)  # UUID as string

    # Task Info
    domain = Column(String(100), nullable=False)  # sales, marketing, seo, customer_dev, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Status
    status = Column(
        String(50), nullable=False
    )  # created, assigned, in_progress, review, completed, failed
    priority = Column(String(50), nullable=False)  # critical, urgent, high, medium, low

    # Assignment
    assigned_employee_id = Column(String(36))  # AI Employee ID
    assigned_by = Column(String(36))  # User ID
    assigned_at = Column(DateTime)

    # Data
    context = Column(JSON)  # Dict[str, Any] - business context
    result = Column(JSON)  # Dict[str, Any] - task result
    error = Column(Text)

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Indexes
    __table_args__ = (
        Index("idx_business_tasks_domain", "domain"),
        Index("idx_business_tasks_status", "status"),
        Index("idx_business_tasks_priority", "priority"),
        Index("idx_business_tasks_assigned_employee_id", "assigned_employee_id"),
    )
