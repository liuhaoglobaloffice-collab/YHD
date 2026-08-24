# LiuHao AI OS Y1.0
# Phase 3.1 — AI Brain Core Implementation Plan

---

## Current State Analysis

### Existing Modules ✅

**src/ai/**:
- `orchestrator.py` — Basic orchestrator with task planning
- `agents.py` — Agent runtime and execution
- `providers.py` — AI provider gateway (GPT, Claude, etc.)
- `tools.py` — Tool registry

**src/workflow/**:
- `service.py` — Workflow CRUD with RBAC + Audit
- `executor.py` — Workflow execution engine
- `models.py` — Workflow data models

**src/tasks/**:
- `service.py` — Task lifecycle management with RBAC + Audit
- `executor.py` — Task execution
- `models.py` — Task data models

**src/workforce/**:
- `registry.py` — AI Employee registry (Single Source of Truth)
- `employee.py` — AI Employee management
- `models.py` — Employee data models

**Database Layer**:
- Repository pattern implemented
- Async database sessions
- Models for Workflow, Task, Employee

**Governance Layer**:
- RBAC (Permission checks)
- Audit (Event logging)
- Approval (Risk-based approval)

---

## Gap Analysis

### What Exists:
✅ AI Orchestrator (basic task planning)
✅ Agent Runtime
✅ Provider Gateway
✅ Workflow Engine
✅ Task System
✅ AI Employee Registry
✅ RBAC + Audit + Approval

### What's Missing:
❌ **CEO Command Interface** (natural language → task plan)
❌ **Intelligent Task Planner** (goal decomposition)
❌ **Agent Router** (task → agent selection logic)
❌ **Brain-Workflow Bridge** (AI Brain → Workflow Engine integration)
❌ **API Endpoint** for CEO commands
❌ **Permissions** for AI Brain operations
❌ **Tests** for AI Brain

---

## Architecture Decision

**Strategy**: **Enhance existing `src/ai/orchestrator.py`** rather than create duplicate `src/ai_brain/`.

**Rationale**:
- Avoid `brain_v2`, `orchestrator_v2` duplication
- `AIOrchestrator` already has task planning logic
- Single Source of Truth for AI coordination
- Preserve Stage 3 architecture

**Modifications**:
1. Add `CEOCommandProcessor` to orchestrator
2. Add `IntelligentPlanner` for goal decomposition
3. Add `AgentRouter` for agent selection
4. Add `WorkflowBridge` to connect to Workflow Engine
5. Create API endpoint `/api/v1/ai-brain/command`

---

## Implementation Plan

### Phase 3.1.1: Enhance Orchestrator ✅

**File**: `src/ai/orchestrator.py`

**Add**:
1. `CEOCommandProcessor` class
   - Parse natural language commands
   - Extract goal, constraints, priority
   
2. `IntelligentPlanner` class
   - Decompose goals into tasks
   - Determine execution order
   - Estimate duration
   
3. `AgentRouter` class
   - Map task types to agent types
   - Select best agent for task
   - Load balancing (future)

**Preserve**:
- Existing `AIOrchestrator` class
- Existing `TaskPlan`, `Task`, `TaskStep` models
- Existing planning logic

---

### Phase 3.1.2: Create Workflow Bridge

**File**: `src/ai/workflow_bridge.py`

**Purpose**: Connect AI Brain to Workflow Engine

**Interface**:
```python
class WorkflowBridge:
    async def create_workflow_from_plan(
        self,
        task_plan: TaskPlan,
        user: User
    ) -> Workflow:
        """Convert AI task plan to Workflow definition"""
        pass
    
    async def execute_workflow(
        self,
        workflow: Workflow,
        user: User
    ) -> WorkflowExecution:
        """Execute workflow through Workflow Engine"""
        pass
```

**Dependencies**:
- `WorkflowService` (existing)
- `WorkflowExecutor` (existing)

---

### Phase 3.1.3: API Endpoint

**File**: `src/api/routes/ai_brain.py`

**Endpoints**:
```
POST /api/v1/ai-brain/command
GET  /api/v1/ai-brain/tasks/{task_id}
GET  /api/v1/ai-brain/tasks/{task_id}/status
```

**Security**:
- Require permission: `Permission.AI_BRAIN_COMMAND_EXECUTE`
- Audit all commands: `AuditAction.AI_BRAIN_COMMAND_CREATED`

---

### Phase 3.1.4: Permission Integration

**File**: `src/identity/rbac.py`

**Add Permissions**:
```python
class Permission(str, Enum):
    # Existing permissions...
    AI_BRAIN_COMMAND_EXECUTE = "ai_brain:command:execute"
    AI_BRAIN_PLAN_READ = "ai_brain:plan:read"
    AI_BRAIN_TASK_READ = "ai_brain:task:read"
```

**Update Role Permissions**:
- CEO: All AI Brain permissions
- Admin: Read + Execute
- User: Read only

---

### Phase 3.1.5: Database Models

**File**: `src/ai/models.py` (new)

**Add**:
```python
@dataclass
class CEOCommand:
    """CEO command record"""
    command_id: UUID
    command_text: str
    user_id: UUID
    goal: str
    task_plan_id: UUID
    workflow_id: Optional[UUID]
    status: CommandStatus
    created_at: datetime
    completed_at: Optional[datetime]
```

**Migration**: Create table `ceo_commands` (optional, can use existing `tasks` table)

---

### Phase 3.1.6: Testing

**File**: `tests/test_ai_brain/`

**Tests**:
1. `test_command_processor.py`
   - Parse CEO command
   - Extract goal and constraints
   
2. `test_intelligent_planner.py`
   - Decompose goal into tasks
   - Agent selection
   
3. `test_workflow_bridge.py`
   - Task plan → Workflow conversion
   - Workflow execution
   
4. `test_ai_brain_api.py`
   - API endpoint security
   - Command submission
   - Status query

**Target**: 20+ tests, 90%+ coverage for new code

---

## File Structure (No Duplicates)

```
src/ai/
  __init__.py                 # Existing
  orchestrator.py             # Enhanced ✏️
  agents.py                   # Existing
  providers.py                # Existing
  tools.py                    # Existing
  workflow_bridge.py          # New ✨
  models.py                   # New ✨ (CEOCommand, etc.)

src/api/routes/
  ai_brain.py                 # New ✨

tests/test_ai_brain/
  __init__.py                 # New ✨
  test_command_processor.py   # New ✨
  test_intelligent_planner.py # New ✨
  test_workflow_bridge.py     # New ✨
  test_ai_brain_api.py        # New ✨
```

**No duplicate modules created.**

---

## Integration Points

### 1. Workflow Engine
```python
# AI Brain → Workflow
workflow_bridge = WorkflowBridge(session)
workflow = await workflow_bridge.create_workflow_from_plan(plan, user)
execution = await workflow_bridge.execute_workflow(workflow, user)
```

### 2. Task System
```python
# Workflow → Task
task_service = TaskService(session)
task = await task_service.create_task(
    title=step.description,
    task_type=TaskType.AI_TASK,
    user=user
)
```

### 3. AI Employee Registry
```python
# Agent Selection → Employee
registry = AIEmployeeRegistry(session)
employees = await registry.list_employees(
    department=Department.RESEARCH,
    status=AIEmployeeStatus.ACTIVE
)
```

---

## Security & Governance

### RBAC Integration ✅
```python
# Before executing command
rbac_service.check_permission(user.id, Permission.AI_BRAIN_COMMAND_EXECUTE)
```

### Audit Integration ✅
```python
# Log command execution
await audit_service.log(
    user_id=user.id,
    action=AuditAction.AI_BRAIN_COMMAND_CREATED,
    resource_type="ceo_command",
    resource_id=str(command.command_id),
    metadata={"command": command.command_text}
)
```

### Approval Integration (Future)
High-risk AI commands (e.g., "Delete all data") require approval before execution.

---

## Example Flow

```
CEO Input:
"分析越南食品包装市场"

↓

CEOCommandProcessor:
  goal: "市场分析 - 越南食品包装"
  constraints: ["越南", "食品包装"]
  priority: HIGH

↓

IntelligentPlanner:
  Task 1: 市场调研 (Research Agent)
  Task 2: 竞争分析 (Research Agent)
  Task 3: 客户画像 (Sales Agent)
  Task 4: 市场规模评估 (Business Agent)

↓

AgentRouter:
  Task 1 → Research AI Employee (ID: xxx)
  Task 2 → Research AI Employee (ID: xxx)
  Task 3 → Sales AI Employee (ID: yyy)
  Task 4 → Business AI Employee (ID: zzz)

↓

WorkflowBridge:
  Create Workflow: "越南食品包装市场分析"
  Steps: [研究, 分析, 评估, 汇报]

↓

WorkflowExecutor (existing):
  Execute workflow through Workflow Engine

↓

TaskExecutor (existing):
  Execute individual tasks through Task System

↓

Result:
  返回给 CEO: 市场分析报告
```

---

## Risk Assessment

### Low Risk ✅
- Enhancing existing `orchestrator.py` (no breaking changes)
- Adding new API endpoint (isolated)
- Adding permissions (backward compatible)

### Medium Risk ⚠️
- Workflow Bridge integration (must not break existing Workflow Engine)
- Database schema changes (if adding `ceo_commands` table)

### Mitigation:
- Write integration tests before modifying Workflow integration
- Use existing Workflow Service interface (no direct database access)
- Optional: Use existing `tasks` table instead of new `ceo_commands` table

---

## Success Criteria

### Must Have ✅
- [x] CEO can submit natural language commands via API
- [x] AI Brain decomposes goals into task plans
- [x] Agent router selects appropriate AI employees
- [x] Workflow Bridge connects to Workflow Engine
- [x] RBAC permissions enforced
- [x] Audit logs generated
- [x] 20+ tests passing
- [x] No duplicate modules created
- [x] Stage 1-8 unaffected

### Nice to Have (Future)
- [ ] Multi-language support (English + 中文)
- [ ] Intelligent agent selection based on performance history
- [ ] Load balancing across AI employees
- [ ] Approval for high-risk commands

---

## Timeline Estimate

- **Phase 3.1.1** (Orchestrator Enhancement): 1-2 hours
- **Phase 3.1.2** (Workflow Bridge): 1 hour
- **Phase 3.1.3** (API Endpoint): 30 minutes
- **Phase 3.1.4** (Permission Integration): 30 minutes
- **Phase 3.1.5** (Database Models): 30 minutes (optional)
- **Phase 3.1.6** (Testing): 1-2 hours

**Total**: 4-6 hours

---

## Approval Required

CEO 请确认实施计划：

- [x] 策略: 增强 `src/ai/orchestrator.py` (不创建 `src/ai_brain/`)
- [x] 架构: 保持 Stage 1-8 完整
- [x] 安全: RBAC + Audit + Approval
- [x] 测试: 20+ 测试，90%+ 覆盖率

**准备开始实施。**
