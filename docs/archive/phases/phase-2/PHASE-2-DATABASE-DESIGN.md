# LiuHao AI OS Y1.0
## Phase 2 — Database Upgrade
## DATABASE MIGRATION DESIGN REPORT

**Date**: 2026-08-22  
**Phase**: Phase 2 — Database Upgrade  
**Objective**: Migrate from in-memory storage to enterprise database  
**Project Root**: D:\LiuHao-AI-OS

---

## Executive Summary

### Current State

**In-Memory Storage** (9 modules):
```
✅ User, Role, Permission        → SQLite (已实现)
✅ AuditLog, ApprovalRequest     → SQLite (已实现)
✅ Session                       → SQLite (已实现)

⚠️ Workflow, WorkflowExecution   → Dict[UUID, *]
⚠️ Task, TaskResult              → Dict[UUID, *]
⚠️ AIEmployee, Performance, Cost → Dict[UUID, *]
⚠️ BusinessTask                  → Dict[UUID, *]
⚠️ OrchestrationTask             → Dict[UUID, *]
⚠️ AgentExecution                → Dict[UUID, *]
⚠️ Knowledge (Documents, Memory) → In-memory
```

**Impact**: 
- 🔴 Data lost on restart
- 🔴 No backup/recovery
- 🔴 No audit trail for business operations
- 🔴 Not production-ready

### Target State

**Enterprise Database Layer**:
```
src/database/
├── __init__.py
├── base.py              # Base model, engine, session
├── repository.py        # Repository pattern base
├── migrations/          # Alembic migrations
└── repositories/        # Specific repositories
    ├── workflow.py
    ├── task.py
    ├── workforce.py
    ├── business.py
    └── knowledge.py
```

**Benefits**:
- ✅ Data persistence
- ✅ Backup/recovery
- ✅ Transaction support
- ✅ Audit trail
- ✅ Scalability
- ✅ Production-ready

---

## 1. Architecture Design

### 1.1 Design Principles

**Repository Pattern**: ✅
- All database access through Repository
- Business logic stays in Services
- Clean separation of concerns

**Single Source of Truth**: ✅
- No duplicate database modules
- No `database_v2` or `new_database`
- Extend existing `src/identity/database.py` → `src/database/`

**Backward Compatibility**: ✅
- Gradual migration
- No breaking changes to Stage 1-8
- Services use same interfaces

**Transaction Management**: ✅
- ACID compliance
- Rollback on failure
- Consistent state

### 1.2 Database Technology

**Current**: SQLite (identity only)  
**Target**: PostgreSQL/MySQL + SQLite fallback

**Rationale**:
- PostgreSQL: Enterprise-grade, JSON support, full-text search
- MySQL: Wide compatibility, proven reliability
- SQLite: Development/testing, zero-config

**Decision**: Support all three via SQLAlchemy

---

## 2. Data Model Migration Plan

### 2.1 Stage 1-2 Models (Already in Database) ✅

**Current Location**: `src/identity/models.py`

```python
✅ User              # SQLAlchemy model
✅ Role              # SQLAlchemy model
✅ Permission        # SQLAlchemy model
✅ AuditLog          # SQLAlchemy model
✅ ApprovalRequest   # SQLAlchemy model (needs completion)
✅ Session           # SQLAlchemy model
```

**Action**: ✅ NO MIGRATION NEEDED

---

### 2.2 Stage 5 Models: Workflow & Task

**Current Location**: 
- `src/workflow/models.py` (@dataclass)
- `src/tasks/models.py` (@dataclass)

**Current Storage**:
- `src/workflow/service.py`: `_workflows: Dict[UUID, Workflow]`
- `src/workflow/executor.py`: `_executions: Dict[UUID, WorkflowExecution]`
- `src/tasks/service.py`: `_tasks: Dict[UUID, Task]`

#### Workflow Models

**Workflow** (dataclass → SQLAlchemy):
```python
@dataclass
class Workflow:
    id: UUID
    name: str
    description: Optional[str]
    created_by: UUID
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    steps: List[WorkflowStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

**New SQLAlchemy Model**:
```python
class WorkflowModel(Base):
    __tablename__ = "workflows"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID as string
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)  # PostgreSQL ARRAY or JSON
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    steps: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=False)  # Serialize WorkflowStep
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    executions: Mapped[List["WorkflowExecutionModel"]] = relationship("WorkflowExecutionModel", back_populates="workflow")
```

**WorkflowExecution**:
```python
class WorkflowExecutionModel(Base):
    __tablename__ = "workflow_executions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # WorkflowExecutionStatus enum
    variables: Mapped[Optional[dict]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    workflow: Mapped["WorkflowModel"] = relationship("WorkflowModel", back_populates="executions")
```

#### Task Models

**Task**:
```python
class TaskModel(Base):
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # TaskType enum
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # TaskStatus enum
    priority: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # TaskPriority enum
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    assigned_agents: Mapped[Optional[List[str]]] = mapped_column(JSON)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    depends_on: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Task IDs
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    subtasks: Mapped[List["TaskModel"]] = relationship("TaskModel", back_populates="parent", remote_side=[parent_task_id])
    parent: Mapped[Optional["TaskModel"]] = relationship("TaskModel", back_populates="subtasks", foreign_keys=[parent_task_id])
    results: Mapped[List["TaskResultModel"]] = relationship("TaskResultModel", back_populates="task")
```

**TaskResult**:
```python
class TaskResultModel(Base):
    __tablename__ = "task_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    output: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text)
    execution_time_ms: Mapped[Optional[int]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    
    # Relationships
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="results")
```

---

### 2.3 Stage 6 Models: AI Workforce

**Current Location**: `src/workforce/models.py` (@dataclass)

**Current Storage**:
- `src/workforce/registry.py`: `_employees: Dict[UUID, AIEmployee]`
- `src/workforce/performance.py`: `_records: Dict[UUID, List[EmployeePerformanceRecord]]`
- `src/workforce/cost.py`: `_records: Dict[UUID, List[EmployeeCostRecord]]`

#### AIEmployee

**AIEmployee**:
```python
class AIEmployeeModel(Base):
    __tablename__ = "ai_employees"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Department enum
    position: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Position enum
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # AgentType enum
    provider: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # AIEmployeeStatus enum
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    performance_records: Mapped[List["EmployeePerformanceModel"]] = relationship("EmployeePerformanceModel", back_populates="employee")
    cost_records: Mapped[List["EmployeeCostModel"]] = relationship("EmployeeCostModel", back_populates="employee")
```

**EmployeePerformanceRecord**:
```python
class EmployeePerformanceModel(Base):
    __tablename__ = "employee_performance"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_employees.id"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    task_type: Mapped[str] = mapped_column(String(100))
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column()  # 0.0-1.0
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    
    # Relationships
    employee: Mapped["AIEmployeeModel"] = relationship("AIEmployeeModel", back_populates="performance_records")
```

**EmployeeCostRecord**:
```python
class EmployeeCostModel(Base):
    __tablename__ = "employee_costs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_employees.id"), nullable=False, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    
    # Relationships
    employee: Mapped["AIEmployeeModel"] = relationship("AIEmployeeModel", back_populates="cost_records")
```

---

### 2.4 Stage 7 Models: Business

**Current Location**: `src/business/models.py` (@dataclass)

**Current Storage**:
- `src/business/registry.py`: `_tasks: Dict[UUID, BusinessTask]`

#### BusinessTask

**BusinessTask**:
```python
class BusinessTaskModel(Base):
    __tablename__ = "business_tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # BusinessDomain enum
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # BusinessTaskPriority enum
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # BusinessTaskStatus enum
    assigned_employee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("ai_employees.id"), index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workflows.id"), index=True)
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    assigned_employee: Mapped[Optional["AIEmployeeModel"]] = relationship("AIEmployeeModel")
    workflow: Mapped[Optional["WorkflowModel"]] = relationship("WorkflowModel")
```

---

### 2.5 Stage 4 Models: Knowledge

**Current Location**: `src/knowledge/` (various modules)

**Current Storage**: In-memory dictionaries

#### Document

**Document**:
```python
class DocumentModel(Base):
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # DocumentType enum
    source: Mapped[Optional[str]] = mapped_column(String(500))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON)  # Vector embedding for RAG
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
```

#### Memory

**Memory**:
```python
class MemoryModel(Base):
    __tablename__ = "memories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # MemoryType enum
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    importance: Mapped[float] = mapped_column(default=0.5, nullable=False)  # 0.0-1.0
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime)
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
```

#### CompanyBrain Entity

**CompanyBrainEntity**:
```python
class CompanyBrainEntityModel(Base):
    __tablename__ = "company_brain_entities"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # EntityType enum
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[Optional[dict]] = mapped_column(JSON)
    relationships: Mapped[Optional[dict]] = mapped_column(JSON)  # {entity_id: relationship_type}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)
```

---

### 2.6 Stage 3 Models: AI Runtime (Optional)

**AgentExecution**: 
- **Decision**: Keep in-memory (ephemeral)
- **Rationale**: Short-lived execution state, no business value after completion
- **Alternative**: Log to AuditLog for permanent record

**OrchestrationTask**:
- **Decision**: Keep in-memory (ephemeral)
- **Rationale**: Internal orchestration state
- **Alternative**: Map to Workflow/Task for business-level persistence

---

## 3. Repository Pattern Design

### 3.1 Base Repository

**File**: `src/database/repository.py`

```python
from typing import Generic, TypeVar, Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

T = TypeVar('T')  # SQLAlchemy model type

class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.
    
    Usage:
        class WorkflowRepository(BaseRepository[WorkflowModel]):
            def __init__(self, session: AsyncSession):
                super().__init__(WorkflowModel, session)
    """
    
    def __init__(self, model_class: type[T], session: AsyncSession):
        self.model_class = model_class
        self.session = session
    
    async def create(self, entity: T) -> T:
        """Create new entity"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, entity_id: str | UUID) -> Optional[T]:
        """Get entity by ID"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == str(entity_id))
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination"""
        result = await self.session.execute(
            select(self.model_class).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def update(self, entity_id: str | UUID, values: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID"""
        await self.session.execute(
            update(self.model_class)
            .where(self.model_class.id == str(entity_id))
            .values(**values)
        )
        await self.session.flush()
        return await self.get_by_id(entity_id)
    
    async def delete(self, entity_id: str | UUID) -> bool:
        """Delete entity by ID"""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == str(entity_id))
        )
        await self.session.flush()
        return result.rowcount > 0
    
    async def exists(self, entity_id: str | UUID) -> bool:
        """Check if entity exists"""
        result = await self.session.execute(
            select(self.model_class.id).where(self.model_class.id == str(entity_id))
        )
        return result.scalar_one_or_none() is not None
```

---

### 3.2 Specific Repositories

#### WorkflowRepository

**File**: `src/database/repositories/workflow.py`

```python
class WorkflowRepository(BaseRepository[WorkflowModel]):
    """Repository for Workflow operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(WorkflowModel, session)
    
    async def list_by_creator(self, user_id: UUID, limit: int = 100) -> List[WorkflowModel]:
        """List workflows by creator"""
        result = await self.session.execute(
            select(WorkflowModel)
            .where(WorkflowModel.created_by == str(user_id))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_enabled(self, limit: int = 100) -> List[WorkflowModel]:
        """List enabled workflows"""
        result = await self.session.execute(
            select(WorkflowModel)
            .where(WorkflowModel.enabled == True)
            .limit(limit)
        )
        return list(result.scalars().all())


class WorkflowExecutionRepository(BaseRepository[WorkflowExecutionModel]):
    """Repository for WorkflowExecution operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(WorkflowExecutionModel, session)
    
    async def list_by_workflow(self, workflow_id: UUID, limit: int = 100) -> List[WorkflowExecutionModel]:
        """List executions for a workflow"""
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.workflow_id == str(workflow_id))
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_by_status(self, status: str, limit: int = 100) -> List[WorkflowExecutionModel]:
        """List executions by status"""
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.status == status)
            .limit(limit)
        )
        return list(result.scalars().all())
```

#### TaskRepository

**File**: `src/database/repositories/task.py`

```python
class TaskRepository(BaseRepository[TaskModel]):
    """Repository for Task operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(TaskModel, session)
    
    async def list_by_workflow(self, workflow_id: UUID) -> List[TaskModel]:
        """List tasks for a workflow"""
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.workflow_id == str(workflow_id))
        )
        return list(result.scalars().all())
    
    async def list_by_status(self, status: str, limit: int = 100) -> List[TaskModel]:
        """List tasks by status"""
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status == status)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_pending(self, limit: int = 100) -> List[TaskModel]:
        """List pending tasks (PENDING or RUNNING)"""
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status.in_(["PENDING", "RUNNING"]))
            .order_by(TaskModel.priority.desc(), TaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
```

#### AIEmployeeRepository

**File**: `src/database/repositories/workforce.py`

```python
class AIEmployeeRepository(BaseRepository[AIEmployeeModel]):
    """Repository for AIEmployee operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(AIEmployeeModel, session)
    
    async def list_by_department(self, department: str) -> List[AIEmployeeModel]:
        """List employees by department"""
        result = await self.session.execute(
            select(AIEmployeeModel).where(AIEmployeeModel.department == department)
        )
        return list(result.scalars().all())
    
    async def list_by_status(self, status: str) -> List[AIEmployeeModel]:
        """List employees by status"""
        result = await self.session.execute(
            select(AIEmployeeModel).where(AIEmployeeModel.status == status)
        )
        return list(result.scalars().all())
    
    async def list_active(self) -> List[AIEmployeeModel]:
        """List active employees"""
        return await self.list_by_status("ACTIVE")
```

#### BusinessTaskRepository

**File**: `src/database/repositories/business.py`

```python
class BusinessTaskRepository(BaseRepository[BusinessTaskModel]):
    """Repository for BusinessTask operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(BusinessTaskModel, session)
    
    async def list_by_domain(self, domain: str, limit: int = 100) -> List[BusinessTaskModel]:
        """List tasks by business domain"""
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.domain == domain)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_by_employee(self, employee_id: UUID) -> List[BusinessTaskModel]:
        """List tasks assigned to an employee"""
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.assigned_employee_id == str(employee_id))
        )
        return list(result.scalars().all())
```

#### KnowledgeRepository

**File**: `src/database/repositories/knowledge.py`

```python
class DocumentRepository(BaseRepository[DocumentModel]):
    """Repository for Document operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentModel, session)
    
    async def search_by_title(self, query: str, limit: int = 20) -> List[DocumentModel]:
        """Search documents by title"""
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.title.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_by_type(self, doc_type: str, limit: int = 100) -> List[DocumentModel]:
        """List documents by type"""
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.doc_type == doc_type)
            .limit(limit)
        )
        return list(result.scalars().all())


class MemoryRepository(BaseRepository[MemoryModel]):
    """Repository for Memory operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MemoryModel, session)
    
    async def list_by_type(self, memory_type: str, limit: int = 100) -> List[MemoryModel]:
        """List memories by type"""
        result = await self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.memory_type == memory_type)
            .order_by(MemoryModel.importance.desc(), MemoryModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_recent(self, limit: int = 50) -> List[MemoryModel]:
        """List recent memories"""
        result = await self.session.execute(
            select(MemoryModel)
            .order_by(MemoryModel.last_accessed.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
```

---

## 4. Migration Strategy

### 4.1 Migration Phases

**Phase A: Database Infrastructure** (Day 1-2)
1. Create `src/database/` module
2. Define all SQLAlchemy models
3. Create base repository
4. Setup Alembic migrations
5. Generate initial migration

**Phase B: Repository Implementation** (Day 3-4)
6. Implement specific repositories
7. Add repository factory/DI
8. Write repository tests

**Phase C: Service Migration** (Day 5-7)
9. Update WorkflowService to use WorkflowRepository
10. Update TaskService to use TaskRepository
11. Update AIEmployeeService to use AIEmployeeRepository
12. Update BusinessService to use BusinessTaskRepository
13. Update Knowledge services to use repositories

**Phase D: Data Migration** (Day 8)
14. Create data migration script (in-memory → database)
15. Test migration with sample data
16. Document rollback procedure

**Phase E: Testing & Validation** (Day 9-10)
17. Run full test suite
18. Performance benchmarking
19. Load testing
20. Production readiness review

---

### 4.2 Backward Compatibility Strategy

**Principle**: No breaking changes to Stage 1-8 APIs

**Approach**:
1. Services maintain same public interfaces
2. Internal storage switches from `Dict` to `Repository`
3. Services handle dataclass ↔ SQLAlchemy model conversion

**Example**: WorkflowService

**Before**:
```python
class WorkflowService:
    def __init__(self):
        self._workflows: Dict[UUID, Workflow] = {}
    
    async def create_workflow(self, ...) -> Workflow:
        workflow = Workflow(...)  # dataclass
        self._workflows[workflow.id] = workflow
        return workflow
```

**After**:
```python
class WorkflowService:
    def __init__(self, repository: WorkflowRepository):
        self.repository = repository
    
    async def create_workflow(self, ...) -> Workflow:
        workflow_model = WorkflowModel(...)  # SQLAlchemy model
        saved = await self.repository.create(workflow_model)
        return self._to_dataclass(saved)  # Convert to dataclass for API
    
    def _to_dataclass(self, model: WorkflowModel) -> Workflow:
        """Convert SQLAlchemy model to dataclass"""
        return Workflow(
            id=UUID(model.id),
            name=model.name,
            ...
        )
    
    def _to_model(self, workflow: Workflow) -> WorkflowModel:
        """Convert dataclass to SQLAlchemy model"""
        return WorkflowModel(
            id=str(workflow.id),
            name=workflow.name,
            ...
        )
```

**Result**: 
- ✅ API unchanged
- ✅ Data persisted
- ✅ No breaking changes

---

### 4.3 Alembic Migration Setup

**File Structure**:
```
src/database/
├── migrations/
│   ├── env.py              # Alembic environment config
│   ├── script.py.mako      # Migration template
│   └── versions/
│       └── 001_initial_migration.py
└── alembic.ini             # Alembic config
```

**Initial Migration** (`001_initial_migration.py`):
```python
"""Initial database schema

Revision ID: 001
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None

def upgrade():
    # Workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text),
        sa.Column('created_by', sa.String(36), nullable=False, index=True),
        sa.Column('version', sa.String(50), default='1.0', nullable=False),
        sa.Column('tags', sa.JSON),
        sa.Column('enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('steps', sa.JSON, nullable=False),
        sa.Column('context', sa.JSON),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    
    # WorkflowExecutions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, index=True),
        sa.Column('variables', sa.JSON),
        sa.Column('result', sa.JSON),
        sa.Column('error', sa.Text),
        sa.Column('metadata', sa.JSON),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime),
    )
    
    # Tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False, index=True),
        sa.Column('description', sa.Text),
        sa.Column('task_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, index=True),
        sa.Column('priority', sa.String(50), nullable=False, index=True),
        sa.Column('created_by', sa.String(36), nullable=False, index=True),
        sa.Column('assigned_agents', sa.JSON),
        sa.Column('workflow_id', sa.String(36), index=True),
        sa.Column('parent_task_id', sa.String(36), sa.ForeignKey('tasks.id'), index=True),
        sa.Column('depends_on', sa.JSON),
        sa.Column('context', sa.JSON),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
    )
    
    # ... (other tables)

def downgrade():
    op.drop_table('workflow_executions')
    op.drop_table('workflows')
    op.drop_table('tasks')
    # ... (other tables)
```

---

## 5. Backup & Recovery

### 5.1 Backup Strategy

**Automated Backups**:
```python
# src/database/backup.py

import subprocess
from datetime import datetime
from pathlib import Path

class DatabaseBackup:
    """Database backup and recovery"""
    
    async def create_backup(self, backup_dir: Path) -> Path:
        """
        Create database backup
        
        PostgreSQL: pg_dump
        MySQL: mysqldump
        SQLite: file copy
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"liuhao_ai_os_{timestamp}.sql"
        
        # Example for PostgreSQL
        subprocess.run([
            "pg_dump",
            "-h", settings.db_host,
            "-U", settings.db_user,
            "-d", settings.db_name,
            "-f", str(backup_file),
        ])
        
        return backup_file
    
    async def restore_backup(self, backup_file: Path):
        """Restore from backup"""
        # Example for PostgreSQL
        subprocess.run([
            "psql",
            "-h", settings.db_host,
            "-U", settings.db_user,
            "-d", settings.db_name,
            "-f", str(backup_file),
        ])
```

**Backup Schedule**:
- Hourly: Last 24 hours
- Daily: Last 30 days
- Weekly: Last 12 weeks
- Monthly: Last 12 months

---

### 5.2 Recovery Procedures

**Scenario 1: Data Corruption**
```bash
# Stop application
systemctl stop liuhao-ai-os

# Restore from latest backup
psql -U liuhao -d liuhao_ai_os -f /backups/latest.sql

# Restart application
systemctl start liuhao-ai-os
```

**Scenario 2: Migration Failure**
```bash
# Rollback migration
alembic downgrade -1

# Fix migration script
# Re-run migration
alembic upgrade head
```

**Scenario 3: Full System Recovery**
```bash
# Recreate database
dropdb liuhao_ai_os
createdb liuhao_ai_os

# Restore from backup
psql -U liuhao -d liuhao_ai_os -f /backups/latest.sql

# Verify data integrity
python -m src.database.verify
```

---

## 6. Testing Strategy

### 6.1 Repository Tests

**Test Coverage**:
- ✅ CRUD operations
- ✅ Query methods
- ✅ Transactions
- ✅ Error handling
- ✅ Concurrent access

**Example**: `tests/test_database/test_repositories/test_workflow.py`
```python
@pytest.mark.asyncio
async def test_workflow_repository_create(db_session):
    """Test creating a workflow"""
    repo = WorkflowRepository(db_session)
    
    workflow = WorkflowModel(
        id=str(uuid4()),
        name="Test Workflow",
        created_by=str(uuid4()),
        steps=[],
    )
    
    saved = await repo.create(workflow)
    assert saved.id == workflow.id
    assert saved.name == workflow.name
    
    # Verify persisted
    retrieved = await repo.get_by_id(workflow.id)
    assert retrieved is not None
    assert retrieved.name == "Test Workflow"
```

---

### 6.2 Service Integration Tests

**Test Coverage**:
- ✅ Service → Repository integration
- ✅ Dataclass ↔ Model conversion
- ✅ Transaction management
- ✅ Error handling

**Example**: `tests/test_workflow/test_service_database.py`
```python
@pytest.mark.asyncio
async def test_workflow_service_with_database(db_session):
    """Test WorkflowService with database backend"""
    repo = WorkflowRepository(db_session)
    service = WorkflowService(repository=repo)
    
    workflow = await service.create_workflow(
        name="Test",
        created_by=uuid4(),
        steps=[],
    )
    
    assert workflow.id is not None
    
    # Verify persistence
    retrieved = await service.get_workflow(workflow.id)
    assert retrieved is not None
    assert retrieved.name == "Test"
```

---

### 6.3 Migration Tests

**Test Coverage**:
- ✅ Schema creation
- ✅ Data migration
- ✅ Rollback
- ✅ Idempotency

---

### 6.4 Performance Tests

**Benchmarks**:
```python
@pytest.mark.benchmark
async def test_workflow_list_performance(db_session):
    """Test listing 1000 workflows"""
    repo = WorkflowRepository(db_session)
    
    # Insert 1000 workflows
    for i in range(1000):
        await repo.create(WorkflowModel(...))
    
    # Measure query time
    start = time.time()
    workflows = await repo.list_all(limit=100)
    duration = time.time() - start
    
    assert duration < 0.1  # Should be < 100ms
    assert len(workflows) == 100
```

---

## 7. Database Configuration

### 7.1 Environment Variables

**New Config** (`src/core/config.py`):
```python
class Settings(BaseSettings):
    # Existing...
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./liuhao_ai_os.db",
        env="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Backup
    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    backup_dir: str = Field(default="./backups", env="BACKUP_DIR")
    backup_schedule_hours: int = Field(default=1, env="BACKUP_SCHEDULE_HOURS")
```

**Example Configurations**:

**Development** (SQLite):
```bash
DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
DATABASE_ECHO=true
```

**Production** (PostgreSQL):
```bash
DATABASE_URL=postgresql+asyncpg://liuhao:password@localhost:5432/liuhao_ai_os
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_ECHO=false
BACKUP_ENABLED=true
BACKUP_DIR=/var/backups/liuhao_ai_os
```

---

### 7.2 Connection Pooling

**Configuration**:
```python
# src/database/base.py

engine = create_async_engine(
    database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
)
```

---

## 8. Risk Assessment

### 8.1 Risks & Mitigation

**Risk 1: Data Loss During Migration** 🔴
- **Mitigation**: 
  - Full backup before migration
  - Test migration on copy first
  - Rollback procedure documented

**Risk 2: Performance Degradation** 🟡
- **Mitigation**:
  - Benchmark before/after
  - Optimize queries
  - Add indexes

**Risk 3: Breaking Changes** 🟡
- **Mitigation**:
  - Maintain API compatibility
  - Comprehensive tests
  - Gradual rollout

**Risk 4: Migration Complexity** 🟢
- **Mitigation**:
  - Phased approach
  - Small, incremental changes
  - Automated testing

---

## 9. Success Criteria

### 9.1 Phase 2 Completion Checklist

- [ ] `src/database/` module created
- [ ] All SQLAlchemy models defined
- [ ] Base repository implemented
- [ ] Specific repositories implemented
- [ ] Alembic migrations setup
- [ ] Initial migration generated
- [ ] All services migrated to repositories
- [ ] Backward compatibility verified
- [ ] Tests pass (>95%)
- [ ] Performance benchmarks met
- [ ] Backup/recovery tested
- [ ] Documentation complete

---

### 9.2 Acceptance Criteria

**Functional**:
- ✅ All data persisted to database
- ✅ No data loss on restart
- ✅ All Stage 1-8 APIs functional
- ✅ Transactions work correctly

**Non-Functional**:
- ✅ Test pass rate ≥ 97.5%
- ✅ Query latency < 50ms (p95)
- ✅ Backup/restore < 1 minute
- ✅ No memory leaks

---

## 10. Timeline

### Estimated Timeline: 10 days

**Day 1-2**: Database Infrastructure
- Create database module
- Define models
- Setup Alembic

**Day 3-4**: Repository Implementation
- Base repository
- Specific repositories
- Repository tests

**Day 5-7**: Service Migration
- Update WorkflowService
- Update TaskService
- Update WorkforceService
- Update BusinessService
- Update KnowledgeService

**Day 8**: Data Migration
- Migration scripts
- Test migration
- Rollback testing

**Day 9-10**: Testing & Validation
- Full test suite
- Performance testing
- Production readiness

---

## 11. Next Steps

### Immediate Actions (After CEO Approval)

1. **Create database structure**:
   ```bash
   mkdir -p src/database/{migrations/versions,repositories}
   ```

2. **Install dependencies**:
   ```bash
   pip install alembic asyncpg psycopg2-binary
   ```

3. **Initialize Alembic**:
   ```bash
   cd src/database
   alembic init migrations
   ```

4. **Define models** in `src/database/models.py`

5. **Generate initial migration**:
   ```bash
   alembic revision --autogenerate -m "Initial schema"
   ```

6. **Run migration**:
   ```bash
   alembic upgrade head
   ```

7. **Begin service migration**

---

## 12. Open Questions for CEO

1. **Database Choice**:
   - PostgreSQL (recommended) or MySQL?
   - Keep SQLite for development?

2. **Backup Schedule**:
   - Hourly backups acceptable?
   - Retention policy?

3. **Migration Timeline**:
   - All services at once, or gradual (Workflow first, then others)?

4. **Production Deployment**:
   - Database hosted where? (Self-hosted / Cloud RDS)
   - Database credentials management?

5. **Data Migration**:
   - Migrate existing in-memory data, or start fresh?
   - (Recommendation: start fresh, as current data is development only)

---

## 13. Conclusion

### Summary

**Phase 2 Database Upgrade** is a critical step to production readiness.

**Benefits**:
- ✅ Data persistence
- ✅ Production-grade reliability
- ✅ Scalability foundation
- ✅ Audit trail
- ✅ Backup/recovery

**Approach**:
- ✅ Repository pattern (clean architecture)
- ✅ Backward compatible (no API changes)
- ✅ Phased migration (low risk)
- ✅ Comprehensive testing

**Recommendation**: **PROCEED**

---

**Design Report Status**: ✅ COMPLETE

**Awaiting CEO Approval**: 
- Database technology choice
- Migration timeline approval
- Production deployment plan

**Ready to Execute**: Upon approval, execution can begin immediately.

---

END OF DATABASE MIGRATION DESIGN REPORT
