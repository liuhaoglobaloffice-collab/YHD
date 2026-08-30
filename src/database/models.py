"""
Database Models - SQLAlchemy ORM Models

Defines database schema for Stage 4-7 entities.

Note: Models from other modules (identity, supplier)
are imported by their respective __init__.py files to avoid circular imports.
"""

from datetime import UTC, datetime

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
# Identity Foundation: Enterprise / Tenant persistence
# =============================================================================


class EnterpriseModel(Base):
    """Minimal enterprise persistence model for identity binding."""

    __tablename__ = "enterprises"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class TenantModel(Base):
    """Minimal tenant persistence model for identity binding."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(64), unique=True, nullable=False)
    tenant_name = Column(String(255), nullable=False)
    enterprise_id = Column(String(36), ForeignKey("enterprises.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_user = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    document = relationship("DocumentModel", back_populates="chunks")


class EmbeddingStorageModel(Base):
    """Phase 2.2 lightweight embedding record model.

    Stores vector metadata and provider identifier in a future-friendly
    shape separate from the document payload itself.

    The unique constraint on (document_id, chunk_id) provides idempotency:
    re-embedding the same chunk updates the existing record rather than
    creating a duplicate.
    """

    __tablename__ = "embedding_storage"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    chunk_id = Column(String(36), nullable=False)
    vector = Column(JSON, nullable=False)
    dimension = Column(Integer, nullable=False, default=3)
    provider = Column(String(80), nullable=False, default="mock")
    embedding_model = Column(String(255), nullable=True, comment="Embedding model name (e.g. nomic-embed-text)")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    document = relationship("DocumentModel", back_populates="embeddings")

    __table_args__ = (
        Index("idx_embedding_doc_chunk", "document_id", "chunk_id", unique=True),
        Index("idx_embedding_provider", "provider"),
    )


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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_accessed_at = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))  # For short-term and working memory expiration

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

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

    # Failure recovery
    retry_count = Column(Integer, nullable=False, default=0, comment="已重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数")

    # Data
    input_data = Column(JSON)  # Dict[str, Any]
    result_data = Column(JSON)  # Dict[str, Any]
    error = Column(Text)

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    deadline = Column(DateTime(timezone=True))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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


class AgentMemoryModel(Base):
    """
    Agent 会话记忆（AI 记忆层 V3）。

    按 用户 × AI员工 自动记录对话/任务历史，供下次执行时回忆注入，
    让鎏灏跨会话记住上下文。

    四级记忆分级策略：
    - 短期（short-term）: 当前会话，7天内，全保留
    - 中期（medium-term）: 1个月内，保留重要对话
    - 长期（long-term）: 永久，保留核心结论/决策
    - 核心（core）: 永远保留，关键业务数据/决策
    """

    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # 操作用户
    agent_id = Column(String(36), nullable=False, index=True)  # AI 员工 UUID
    role = Column(String(20), nullable=False, default="user")  # user / assistant
    content = Column(Text, nullable=False)
    task_id = Column(String(64), nullable=True)  # 可选：执行记录 ID
    # 记忆分级存储
    memory_level = Column(String(20), nullable=False, default="short_term")
    # 重要性评分 0.0-1.0，决定保留优先级
    importance = Column(Float, nullable=False, default=0.5)
    # 是否永久保留（核心记忆永远不清理）
    is_core = Column(Boolean, nullable=False, default=False)
    # 过期时间（自动清理）
    expires_at = Column(DateTime(timezone=True), nullable=True)
    # 访问统计
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, nullable=False, default=0)
    # 预留：tokens/耗时等扩展
    meta = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    __table_args__ = (
        Index("idx_agent_memories_user_agent", "user_id", "agent_id", "created_at"),
        Index("idx_agent_memories_level_expires", "memory_level", "expires_at"),
        Index("idx_agent_memories_core", "is_core"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "content": self.content,
            "task_id": self.task_id,
            "memory_level": self.memory_level,
            "importance": self.importance,
            "is_core": self.is_core,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
            "meta": self.meta,
            "created_at": self.created_at.isoformat(),
        }


class AiCostRecordModel(Base):
    """
    AI 成本追踪记录（V3 · 能量系统落地）。

    记录每次 AI 任务执行的 Token 用量、估算成本与耗时，
    供"老板视角"成本仪表盘使用。
    """

    __tablename__ = "ai_cost_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # 操作用户
    employee_id = Column(String(36), nullable=True, index=True)  # AI 员工 UUID
    agent_type = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=False)  # openai / ollama / mock ...
    model = Column(String(100), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)  # 估算成本（USD）
    latency_ms = Column(Float, nullable=True)
    status = Column(String(20), default="success")  # success / failed
    meta = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    __table_args__ = (
        Index("idx_ai_cost_records_user_created", "user_id", "created_at"),
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
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

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
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Metadata
    meta = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

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
    assigned_at = Column(DateTime(timezone=True))

    # V4: 多租户归属（int = users.id）。owner_user_id=归属账号，created_by=代建者
    owner_user_id = Column(Integer, index=True)
    created_by = Column(Integer, nullable=True)

    # Data
    context = Column(JSON)  # Dict[str, Any] - business context
    result = Column(JSON)  # Dict[str, Any] - task result
    error = Column(Text)

    # Metadata
    meta = Column(JSON)
    tags = Column(JSON)  # List[str]

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True))

    # Indexes
    __table_args__ = (
        Index("idx_business_tasks_domain", "domain"),
        Index("idx_business_tasks_status", "status"),
        Index("idx_business_tasks_priority", "priority"),
        Index("idx_business_tasks_assigned_employee_id", "assigned_employee_id"),
    )


# =============================================================================
# Weekly Meeting Chat
# =============================================================================


class MeetingModel(Base):
    """Weekly meeting model."""

    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    status = Column(String(20), nullable=False, default="active")  # active, completed
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_meetings_date", "date"),
        Index("idx_meetings_status", "status"),
    )


class MessageModel(Base):
    """Meeting chat message model."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    sender = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="member")  # admin, member
    content = Column(Text, nullable=False)
    time = Column(String(10), nullable=False)  # HH:MM

    # Relationships
    meeting = relationship("MeetingModel", backref="messages")

    __table_args__ = (
        Index("idx_messages_meeting_id", "meeting_id"),
    )


class ProductModel(Base):
    """产品目录模型"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, comment="产品ID")
    name = Column(String(255), nullable=False, comment="产品名称")
    category = Column(String(100), nullable=True, comment="产品类别")
    description = Column(Text, nullable=True, comment="产品描述")
    price = Column(Float, nullable=True, comment="价格（USD）")
    unit = Column(String(50), nullable=True, default="件", comment="单位")
    moq = Column(Integer, nullable=True, comment="最小起订量")
    image_url = Column(String(500), nullable=True, comment="图片URL")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/inactive")
    tags = Column(String(500), nullable=True, comment="标签（逗号分隔）")

    # 归属
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), comment="更新时间")

    __table_args__ = (
        Index("idx_products_category", "category"),
        Index("idx_products_status", "status"),
        Index("idx_products_tenant", "tenant_id"),
    )


# =============================================================================
# P1: 老板目标中心 + 失败恢复链
# =============================================================================


class GoalModel(Base):
    """老板目标模型 — 持久化存储目标、KPI、进度、预算。"""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="目标ID")
    title = Column(String(500), nullable=False, comment="目标标题")
    description = Column(Text, nullable=True, comment="目标描述")

    # 状态
    status = Column(String(50), nullable=False, default="draft", comment="状态: draft/active/completed/failed/cancelled")

    # 优先级
    priority = Column(String(50), nullable=False, default="normal", comment="优先级: low/normal/high/critical")

    # KPI
    kpi_name = Column(String(255), nullable=True, comment="KPI 名称")
    kpi_target = Column(Float, nullable=True, comment="KPI 目标值")
    kpi_current = Column(Float, nullable=True, default=0.0, comment="KPI 当前值")
    kpi_unit = Column(String(50), nullable=True, comment="KPI 单位")

    # 预算
    budget_total = Column(Float, nullable=True, comment="总预算（USD）")
    budget_spent = Column(Float, nullable=True, default=0.0, comment="已花费（USD）")

    # 时间范围
    time_start = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    time_end = Column(DateTime(timezone=True), nullable=True, comment="截止时间")

    # 执行计划（JSON 存储 Parser+Planner 输出）
    plan_data = Column(JSON, nullable=True, comment="执行计划数据")
    workflow_id = Column(String(36), nullable=True, comment="关联的 Workflow ID")

    # 进度
    progress_pct = Column(Float, nullable=True, default=0.0, comment="完成进度百分比 0-100")

    # 归属
    created_by = Column(Integer, nullable=False, comment="创建人ID (OWNER)")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), comment="更新时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")

    __table_args__ = (
        Index("idx_goals_status", "status"),
        Index("idx_goals_priority", "priority"),
        Index("idx_goals_created_by", "created_by"),
        Index("idx_goals_tenant", "tenant_id"),
        Index("idx_goals_workflow", "workflow_id"),
    )


class FailureRecordModel(Base):
    """失败恢复记录模型 — 记录任务失败原因、策略调整、经验沉淀。"""

    __tablename__ = "failure_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True, comment="关联目标ID")
    task_id = Column(String(36), nullable=True, comment="关联任务ID")
    workflow_id = Column(String(36), nullable=True, comment="关联 Workflow ID")

    # 失败分类
    failure_category = Column(String(100), nullable=False, comment="失败分类: provider_error/network_error/timeout/rate_limit/auth_error/agent_error/business_logic_error/unknown")
    failure_summary = Column(Text, nullable=False, comment="失败摘要")
    failure_detail = Column(Text, nullable=True, comment="失败详情/错误堆栈")

    # 重试信息
    retry_count = Column(Integer, nullable=False, default=0, comment="已重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数")

    # 策略调整
    strategy_action = Column(String(100), nullable=True, comment="策略调整动作: switch_agent/switch_provider/adjust_params/change_approach/request_boss/abort")
    strategy_detail = Column(JSON, nullable=True, comment="策略调整详情")

    # 经验沉淀
    lesson_learned = Column(Text, nullable=True, comment="经验教训")
    is_successful = Column(Boolean, nullable=True, comment="最终是否成功恢复")

    # 安全阈值
    threshold_exceeded = Column(Boolean, nullable=False, default=False, comment="是否超过安全阈值")
    boss_notified = Column(Boolean, nullable=False, default=False, comment="是否已通知老板")
    boss_decision = Column(String(500), nullable=True, comment="老板决策")

    # 归属
    created_by = Column(Integer, nullable=False, comment="记录人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间")
    resolved_at = Column(DateTime(timezone=True), nullable=True, comment="解决时间")

    __table_args__ = (
        Index("idx_failure_records_goal", "goal_id"),
        Index("idx_failure_records_task", "task_id"),
        Index("idx_failure_records_category", "failure_category"),
        Index("idx_failure_records_tenant", "tenant_id"),
    )
