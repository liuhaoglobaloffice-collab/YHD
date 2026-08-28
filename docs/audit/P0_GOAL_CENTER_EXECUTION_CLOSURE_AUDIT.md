# P0 审计报告：Goal Center 执行闭环

> **日期**: 2026-08-28
> **基线**: v1.0.0（commit eaba5262）
> **分支**: develop
> **状态**: HEALTHY

---

## 一、审计范围

本次 P0 审计聚焦 Goal Center 的执行闭环，仅覆盖两个最高优先级问题：

| 编号 | 问题 | 状态 |
|------|------|------|
| P0 #1 | WorkflowExecutor 创建 Task 后必须真正执行 | **已修复** |
| P0 #2 | WorkflowExecution 状态必须持久化到数据库，重启后不丢失 | **已修复** |

**审计边界**：`src/workflow/`、`src/tasks/`、`src/ai/`（GoalService）、`src/database/`（WorkflowExecution 相关 repository/converter）

---

## 二、审计发现与修复

### P0 #1：WorkflowExecutor 创建 Task 后必须真正执行

**审计发现**：

`WorkflowExecutor._execute_task_step()` 创建 Task 后直接返回，未调用任何执行器，导致 Task 永远停留在 `pending` 状态，Workflow 执行链在 Task 创建后断裂。

**修复方案**：

1. **`_execute_task_step()` 注入真实执行**：创建 Task 后立即调用 `TaskExecutor.execute_task(task.id, user)`，将 Task 状态推进到 `running` → `completed`/`failed`
2. **异常传播**：如果 `TaskExecutor` 抛出异常或返回 `success=False`，重新抛出异常，使 `execute_workflow()` 的 `except` 块捕获并将 Workflow 状态设为 `FAILED`
3. **GoalService 注入依赖**：`GoalService.execute_goal_workflow()` 创建 `WorkflowExecutor` 时注入 `RBACService`、`WorkflowService`、`TaskService`、`TaskExecutor`，确保执行链路完整

**执行闭环路径**：

```
GoalService.execute_goal_workflow()
  └─ WorkflowExecutor.execute_workflow()
       └─ _execute_step() → _execute_task_step()
            ├─ TaskService.create_task()          → 创建 Task（pending）
            ├─ TaskExecutor.execute_task()         → 真实执行（running→completed/failed）
            └─ 异常/失败 → 传播到 execute_workflow() → FAILED
```

### P0 #2：WorkflowExecution 状态持久化到数据库

**审计发现**：

`WorkflowExecutor` 仅将 `WorkflowExecution` 保存在内存字典 `_executions` 中，重启后全部丢失。没有任何持久化机制。

**修复方案**：

新增 `_persist_execution()` 方法，在每次关键状态变更时同步写入数据库：

| 状态 | 触发点 | 持久化字段 |
|------|--------|-----------|
| `PENDING` | `execute_workflow()` 创建 execution 后 | status, workflow_id, variables, meta |
| `RUNNING` | 开始执行步骤前 | status, started_at, variables |
| `COMPLETED` | 所有步骤执行成功后 | status, completed_at, result, variables |
| `FAILED` | 异常捕获后 | status, completed_at, error, variables |
| `PAUSED` | `pause_execution()` | status |
| `CANCELLED` | `cancel_execution()` | status, completed_at |

**持久化保障**：
- 使用现有 `WorkflowExecutionRepository` + `AsyncSession.commit()` 架构
- 异常路径（`try/except` 块内）也会持久化 `FAILED` 状态
- `model_to_workflow_execution()` 支持从数据库读取后恢复完整状态
- 修复了 `user_id` 非 UUID 格式时的转换兼容性问题

---

## 三、修改文件汇总

| 文件 | 改动量 | 作用 |
|------|--------|------|
| `src/workflow/executor.py` | +111 / -6 | 核心：`_persist_execution`、`_execute_task_step` 异常传播、`event_bus.publish` 同步修复 |
| `src/workflow/models.py` | +3 / -0 | 添加 `result: Optional[Dict[str, Any]] = None` 字段 |
| `src/ai/goal_service.py` | +19 / -5 | 注入 `RBACService`、`WorkflowService`、`TaskService`、`TaskExecutor` |
| `src/database/repositories/converters.py` | +12 / -3 | `model_to_workflow_execution` 兼容非 UUID user_id |
| `tests/integration/test_workflow_executor.py` | **新文件** | 11 个集成测试 |

**未修改文件**：`src/tasks/executor.py`、`src/tasks/service.py`、`src/database/repositories/workflow.py`、`src/identity/rbac.py`、`src/identity/audit.py` —— 全部复用现有代码。

---

## 四、测试覆盖

### 新增测试（11 个）

| 测试函数 | 覆盖场景 |
|----------|---------|
| `test_workflow_executor_calls_task_executor` | P0 #1：TaskExecutor 被调用 |
| `test_workflow_executor_skips_task_executor_when_not_available` | 无 TaskExecutor 时只创建 Task |
| `test_workflow_execution_completed` | 完整执行：pending→running→completed |
| `test_workflow_execution_failed` | 异常传播：pending→running→failed |
| `test_workflow_execution_persisted_to_db` | P0 #2：COMPLETED 写入 DB |
| `test_workflow_execution_failed_persisted_to_db` | 异常路径 FAILED 写入 DB |
| `test_workflow_execution_status_from_db` | 从 DB 重新读取后状态一致 |
| `test_task_executor_no_assigned_employee` | 无 assigned employee 不伪造完成 |
| `test_goal_service_creates_executor_with_task_executor` | GoalService 完整链路 |
| `test_pause_execution_persisted` | PAUSED 状态持久化 |
| `test_cancel_execution_persisted` | CANCELLED 状态持久化 |

### 回归验证

| 项目 | 结果 |
|------|------|
| 后端 pytest（全部） | **296 passed, 0 failed** |
| 前端测试 | **94 passed, 3 files** |
| 前端 build | **91 modules, build 成功** |
| `git diff --check` | **无 whitespace 错误** |

---

## 五、修复过程中发现并修复的附加问题

| 问题 | 位置 | 修复 |
|------|------|------|
| `EventBus.publish()` 为同步方法，但被 `await` 调用 | `src/workflow/executor.py::execute_workflow` | 移除 `await` |
| `WorkflowExecution` 缺少 `result` 字段 | `src/workflow/models.py` | 添加 `result: Optional[Dict[str, Any]] = None` |
| `model_to_workflow_execution` 强制将 `user_id` 转为 UUID | `src/database/repositories/converters.py` | 添加非 UUID 兼容逻辑 |
| `GoalService` 创建 `WorkflowExecutor` 不传 `RBACService`，导致 `get_dependency` 失败 | `src/ai/goal_service.py` | 显式注入所有依赖 |

---

## 六、审计结论

| 维度 | 结论 |
|------|------|
| P0 #1 执行闭环 | **已闭环**：Task 创建后经 `TaskExecutor` 真实执行，状态流转完整 |
| P0 #2 状态持久化 | **已闭环**：6 种状态变更均持久化到数据库，异常路径不丢失 |
| 无 Mock/Placeholder 冒充 | **验证通过**：生产路径使用真实 `TaskExecutor`，无 assigned employee 时不伪造 |
| API Contract 未变更 | **验证通过**：`execute_workflow()` 签名、返回值、异常类型均未改变 |
| 未修改无关模块 | **验证通过**：仅修改 4 个必要文件，所有服务复用现有代码 |
| 测试覆盖 | **充分**：11 个新增集成测试覆盖全部关键场景 |
| 回归验证 | **全部通过**：后端 296 + 前端 94 + 前端 build 均通过 |

**总体状态：HEALTHY，无 blocker。**