# 短板能力推进实施计划

> **目标:** 将 4 项短板能力（动态信任 L1→L3、主动经营 L1→L3、AI 集体智能 L1→L2-L3、老板不在线 L0→L2）在现有模块内最小化扩展
> **架构:** 分阶段递进，每阶段 TDD + 回归验证后再推进下一阶段，不新建模块
> **约束:** 不新增 Phase 9/10、不改变总体架构、不新建模块、保持 571+ passed 0 failed

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/ai/agent_router.py` | 修改 | 实现真实信任评分 + 路由降权 |
| `src/modules/ceo_dashboard_module.py` | 修改 | 扩展业务级告警 + 摘要报告 |
| `src/knowledge/memory.py` | 修改 | 新增 Agent 经验存储/检索 |
| `src/workforce/employee.py` | 修改 | 执行链路注入经验共享 |
| `tests/ai/test_trust_scoring.py` | 新建 | 信任评分测试 |
| `tests/modules/test_business_alerts.py` | 新建 | 业务告警测试 |
| `tests/ai/test_collective_intelligence.py` | 新建 | 集体智能测试 |
| `tests/modules/test_summary_report.py` | 新建 | 摘要报告测试 |

---

## 阶段 1：动态信任体系 + 主动经营（并行）

### Task 1: 实现能力评分（基于 EmployeePerformanceModel）

**Files:**
- Modify: `src/ai/agent_router.py:136-151`
- Test: `tests/ai/test_trust_scoring.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_trust_scoring.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from src.ai.agent_router import AgentRouter


@pytest.mark.asyncio
async def test_capability_score_with_performance_data():
    """有性能记录时返回真实 success_rate。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock: EmployeePerformanceModel 查询返回 success_rate=0.85
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(success_rate=0.85)
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_capability_score(employee_id=str(uuid4()))
    assert score == 0.85


@pytest.mark.asyncio
async def test_capability_score_no_data_returns_default():
    """无性能记录时返回 0.5 默认值。"""
    session = MagicMock()
    router = AgentRouter(session)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_capability_score(employee_id=str(uuid4()))
    assert score == 0.5
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_trust_scoring.py::test_capability_score_with_performance_data -v`
Expected: FAIL (get_agent_capability_score 是同步方法且返回 1.0)

- [ ] **Step 3: 实现**

```python
# src/ai/agent_router.py — 替换 get_agent_capability_score 方法

async def get_agent_capability_score(self, employee_id: str) -> float:
    """
    基于员工历史性能数据计算能力评分。

    数据源: EmployeePerformanceModel.success_rate
    无记录时返回 0.5 中性默认值，不阻塞路由。
    """
    from sqlalchemy import select
    from ..database.models import EmployeePerformanceModel

    try:
        result = await self.session.execute(
            select(EmployeePerformanceModel.success_rate)
            .where(EmployeePerformanceModel.employee_id == employee_id)
            .order_by(EmployeePerformanceModel.period_start.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return float(row)
        return 0.5
    except Exception as e:
        logger.warning(f"Failed to get capability score for {employee_id}: {e}")
        return 0.5
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_trust_scoring.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ai/agent_router.py tests/ai/test_trust_scoring.py
git commit -m "feat: 实现基于 EmployeePerformanceModel 的真实能力评分"
```

---

### Task 2: 实现风险评分（基于 FailureRecordModel）

**Files:**
- Modify: `src/ai/agent_router.py`
- Test: `tests/ai/test_trust_scoring.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_trust_scoring.py — 追加

@pytest.mark.asyncio
async def test_risk_score_no_failures_returns_low_risk():
    """无失败记录时风险评分低（0.1）。"""
    session = MagicMock()
    router = AgentRouter(session)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_risk_score(employee_id=str(uuid4()))
    assert score <= 0.2  # 无失败 = 低风险


@pytest.mark.asyncio
async def test_risk_score_with_failures():
    """有未恢复失败时风险评分升高。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock: 通过 task_id 关联查到 3 条失败，1 条未恢复
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.total = 3
    mock_row.unrecovered = 1
    mock_result.first.return_value = mock_row
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_risk_score(employee_id=str(uuid4()))
    assert score > 0.2  # 有未恢复失败 = 风险升高
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_trust_scoring.py::test_risk_score_no_failures_returns_low_risk -v`
Expected: FAIL (方法不存在)

- [ ] **Step 3: 实现**

```python
# src/ai/agent_router.py — 新增方法

async def get_agent_risk_score(self, employee_id: str) -> float:
    """
    基于失败恢复记录计算风险评分。

    通过 tasks.assigned_to 关联 FailureRecordModel，
    统计未恢复失败比例。无记录时返回 0.1（低风险默认）。
    """
    from sqlalchemy import select, func, text

    try:
        # 通过 task_id 关联：tasks 表中 assigned_to 含该 employee_id 的任务
        # → FailureRecordModel 中 task_id 匹配 → 统计 is_successful=False
        sql = text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN fr.is_successful = 0 OR fr.is_successful IS NULL THEN 1 END) as unrecovered
            FROM failure_records fr
            WHERE fr.task_id IN (
                SELECT id FROM tasks WHERE assigned_to LIKE :emp_pattern
            )
        """)

        result = await self.session.execute(
            sql, {"emp_pattern": f'%{employee_id}%'}
        )
        row = result.first()

        if row and row.total > 0:
            unrecovered_ratio = row.unrecovered / row.total
            # 风险评分 = 未恢复比例（0.0-1.0，越高越危险）
            return min(unrecovered_ratio, 1.0)
        return 0.1  # 无失败 = 低风险
    except Exception as e:
        logger.warning(f"Failed to get risk score for {employee_id}: {e}")
        return 0.5
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_trust_scoring.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ai/agent_router.py tests/ai/test_trust_scoring.py
git commit -m "feat: 实现基于 FailureRecordModel 的风险评分"
```

---

### Task 3: 实现信任评分（综合能力+风险+权限）

**Files:**
- Modify: `src/ai/agent_router.py`
- Test: `tests/ai/test_trust_scoring.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_trust_scoring.py — 追加

@pytest.mark.asyncio
async def test_trust_score_combines_capability_and_risk():
    """信任评分综合能力和风险。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock capability=0.8, risk=0.2
    mock_perf = MagicMock()
    mock_perf.scalar_one_or_none.return_value = MagicMock(success_rate=0.8)
    # 第一次调用返回 performance，第二次返回 failure 统计
    mock_fail = MagicMock()
    mock_fail_row = MagicMock()
    mock_fail_row.total = 5
    mock_fail_row.unrecovered = 1
    mock_fail.first.return_value = mock_fail_row

    session.execute = AsyncMock(side_effect=[mock_perf, mock_fail])

    score = await router.get_agent_trust_score(employee_id=str(uuid4()))
    assert 0.0 <= score <= 1.0
    # 能力 0.8 * 0.4 + (1-风险 0.2) * 0.3 + 权限 0.5 * 0.3 = 0.32+0.24+0.15 = 0.71
    assert score > 0.5  # 高能力低风险 = 高信任
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_trust_scoring.py::test_trust_score_combines_capability_and_risk -v`
Expected: FAIL (方法不存在)

- [ ] **Step 3: 实现**

```python
# src/ai/agent_router.py — 新增方法

async def get_agent_trust_score(self, employee_id: str) -> float:
    """
    综合信任评分 = 能力(40%) + 风险(30%) + 权限范围(30%)。

    - 能力: get_agent_capability_score (success_rate)
    - 风险: 1 - get_agent_risk_score (低风险 = 高信任)
    - 权限范围: 基于 RBAC 权限数量归一化（默认 0.5）
    """
    capability = await self.get_agent_capability_score(employee_id)
    risk = await self.get_agent_risk_score(employee_id)

    # 权限范围评分：当前简化为 0.5（后续可从 RBAC 查询权限数量归一化）
    permission_score = 0.5

    trust = (capability * 0.4) + ((1.0 - risk) * 0.3) + (permission_score * 0.3)
    return round(min(max(trust, 0.0), 1.0), 4)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_trust_scoring.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ai/agent_router.py tests/ai/test_trust_scoring.py
git commit -m "feat: 实现综合信任评分（能力+风险+权限）"
```

---

### Task 4: 修改路由逻辑（按信任评分排序+降权）

**Files:**
- Modify: `src/ai/agent_router.py:80-134`
- Test: `tests/ai/test_trust_scoring.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_trust_scoring.py — 追加

@pytest.mark.asyncio
async def test_low_trust_employee_skipped_in_routing():
    """信任评分低于 0.3 的员工被跳过。"""
    session = MagicMock()
    router = AgentRouter(session)

    # 两个员工，一个高信任一个低信任
    from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position

    good_emp = MagicMock()
    good_emp.id = uuid4()
    good_emp.name = "优秀员工"
    good_emp.department = Department.SALES
    good_emp.position = Position.SALES_REPRESENTATIVE
    good_emp.status = AIEmployeeStatus.ACTIVE

    bad_emp = MagicMock()
    bad_emp.id = uuid4()
    bad_emp.name = "低信任员工"
    bad_emp.department = Department.SALES
    bad_emp.position = Position.SALES_REPRESENTATIVE
    bad_emp.status = AIEmployeeStatus.ACTIVE

    router.registry = MagicMock()
    router.registry.list_employees = AsyncMock(return_value=[bad_emp, good_emp])

    # Mock trust scores: bad=0.1, good=0.8
    call_count = [0]
    original_trust = router.get_agent_trust_score

    async def mock_trust(employee_id):
        call_count[0] += 1
        if employee_id == str(bad_emp.id):
            return 0.1
        return 0.8

    router.get_agent_trust_score = mock_trust

    task = {"task_id": str(uuid4()), "name": "test", "agent_type": "sales", "description": "test"}
    assignment = await router.route_task(task)

    # 应选择高信任员工
    assert str(assignment.employee_id) == str(good_emp.id)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_trust_scoring.py::test_low_trust_employee_skipped_in_routing -v`
Expected: FAIL (当前路由选第一个，不按信任评分排序)

- [ ] **Step 3: 实现**

```python
# src/ai/agent_router.py — 修改 route_task 方法（第 80-134 行）

async def route_task(self, task: Dict) -> AgentAssignment:
    """Route single task to specific AI employee, sorted by trust score."""
    agent_type = task.get("agent_type", "business")
    task_id = UUID(task["task_id"])

    mapping = self.AGENT_MAPPING.get(agent_type, self.AGENT_MAPPING["business"])

    try:
        employees = await self.registry.list_employees(
            department=mapping["department"], status=AIEmployeeStatus.ACTIVE
        )

        if employees:
            # 按信任评分排序选择：高分优先，低于 0.3 阈值的跳过
            TRUST_THRESHOLD = 0.3
            scored = []
            for emp in employees:
                trust = await self.get_agent_trust_score(str(emp.id))
                if trust >= TRUST_THRESHOLD:
                    scored.append((emp, trust))

            if not scored:
                # 所有员工都低于阈值时仍选最高的，但记录警告
                scored = [
                    (emp, await self.get_agent_trust_score(str(emp.id)))
                    for emp in employees
                ]
                logger.warning(
                    f"All employees below trust threshold {TRUST_THRESHOLD} "
                    f"for task '{task.get('name')}'"
                )

            scored.sort(key=lambda x: x[1], reverse=True)
            employee, trust_score = scored[0]

            assignment = AgentAssignment(
                task_id=task_id,
                task_description=task.get("description", task["name"]),
                agent_type=agent_type,
                employee_id=employee.id,
                employee_name=employee.name,
                department=employee.department.value,
                position=employee.position.value,
                confidence=trust_score,
                reason=f"Selected {employee.name} (trust={trust_score:.2f})",
            )
        else:
            error_msg = (
                f"No {agent_type} AI employee available for task '{task.get('name', 'unknown')}'. "
                "Register an AI employee with the required department/position before activating goals."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    except Exception as e:
        logger.error(f"Error routing task {task_id}: {e}")
        raise ValueError(f"Failed to route task '{task.get('name', 'unknown')}': {e}") from e

    return assignment
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_trust_scoring.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ai/agent_router.py tests/ai/test_trust_scoring.py
git commit -m "feat: 路由按信任评分排序，低分员工自动降权跳过"
```

---

### Task 5: 实现业务异常扫描（主动经营）

**Files:**
- Modify: `src/modules/ceo_dashboard_module.py`
- Test: `tests/modules/test_business_alerts.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/modules/test_business_alerts.py
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from src.modules.ceo_dashboard_module import CEODashboardModule


def test_business_anomalies_no_data_returns_empty():
    """无数据时返回空告警列表。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))

    alerts = module.scan_business_anomalies(session)
    assert alerts == []


def test_business_anomalies_lead_decline():
    """线索下降时生成 lead_decline 告警。"""
    module = CEODashboardModule()
    session = MagicMock()

    # Mock: 本周线索 2 条，上周 10 条 → 下降 80%
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (10, 2)  # (last_week, this_week)
    session.execute = AsyncMock(return_value=mock_result)

    alerts = module.scan_business_anomalies(session)
    lead_alerts = [a for a in alerts if a["type"] == "lead_decline"]
    assert len(lead_alerts) == 1
    assert lead_alerts[0]["level"] == "warning"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/modules/test_business_alerts.py -v`
Expected: FAIL (scan_business_anomalies 方法不存在)

- [ ] **Step 3: 实现**

```python
# src/modules/ceo_dashboard_module.py — 新增方法

def scan_business_anomalies(self, session) -> List[Dict[str, Any]]:
    """扫描业务异常并生成业务级告警。

    检测项：
    - lead_decline: 线索数量周环比下降超过 50%
    - customer_churn: 客户状态变为 lost/churned
    - supplier_risk_change: 供应商风险等级上升
    """
    alerts = []
    now = datetime.now(UTC)

    try:
        # 线索下降检测
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM leads WHERE created_at >= date('now', '-7 days')) as this_week,
                (SELECT COUNT(*) FROM leads WHERE created_at >= date('now', '-14 days')
                 AND created_at < date('now', '-7 days')) as last_week
        """)).fetchone()

        if result:
            this_week, last_week = result[0] or 0, result[1] or 0
            if last_week > 0:
                decline_rate = (last_week - this_week) / last_week
                if decline_rate > 0.5:
                    alerts.append({
                        "id": "alert_lead_decline",
                        "type": "lead_decline",
                        "level": "warning",
                        "title": "线索数量下降",
                        "message": f"本周线索 {this_week} 条，较上周 {last_week} 条下降 {decline_rate*100:.0f}%",
                        "timestamp": now.isoformat(),
                    })
    except Exception as e:
        logger.warning(f"Lead decline scan failed: {e}")

    try:
        # 客户流失检测
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT COUNT(*) FROM leads WHERE status = 'lost'
        """)).fetchone()
        if result and result[0] > 0:
            alerts.append({
                "id": "alert_customer_churn",
                "type": "customer_churn",
                "level": "warning",
                "title": "客户流失",
                "message": f"{result[0]} 个客户状态为流失",
                "timestamp": now.isoformat(),
            })
    except Exception as e:
        logger.warning(f"Customer churn scan failed: {e}")

    try:
        # 供应商风险变化检测
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT COUNT(*) FROM suppliers WHERE risk_level = 'high'
        """)).fetchone()
        if result and result[0] > 0:
            alerts.append({
                "id": "alert_supplier_risk",
                "type": "supplier_risk_change",
                "level": "warning",
                "title": "供应商风险升高",
                "message": f"{result[0]} 个供应商风险等级为高",
                "timestamp": now.isoformat(),
            })
    except Exception as e:
        logger.warning(f"Supplier risk scan failed: {e}")

    return alerts
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/modules/test_business_alerts.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/modules/ceo_dashboard_module.py tests/modules/test_business_alerts.py
git commit -m "feat: 实现业务级异常扫描（线索下降/客户流失/供应商风险）"
```

---

### Task 6: 阶段 1 回归验证

- [ ] **Step 1: 运行完整回归测试**

Run: `python -m pytest -q`
Expected: 571+ passed, 0 failed, Failure Recovery Chain 无回归

- [ ] **Step 2: 确认 E2E 链路不受影响**

Run: `python -m pytest tests/integration/test_e2e_chain.py -v`
Expected: 5 passed

---

## 阶段 2：AI 集体智能（阶段 1 验证通过后）

### Task 7: 扩展 MemoryService 支持 Agent 经验存储

**Files:**
- Modify: `src/knowledge/memory.py`
- Test: `tests/ai/test_collective_intelligence.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_collective_intelligence.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from src.knowledge.memory import MemoryService


@pytest.mark.asyncio
async def test_store_agent_experience():
    """Agent 经验可写入共享知识库。"""
    session = MagicMock()
    service = MemoryService(session)
    emp_id = str(uuid4())

    result = await service.store_agent_experience(
        employee_id=emp_id,
        task_type="sales",
        result_summary="成功完成客户开发，转化率 15%"
    )
    assert result is not None


@pytest.mark.asyncio
async def test_recall_agent_experience():
    """可按 task_type 检索同类经验。"""
    session = MagicMock()
    service = MemoryService(session)

    # Mock 查询返回经验记录
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.content = "成功完成客户开发，转化率 15%"
    mock_row.employee_id = str(uuid4())
    mock_result.scalars.return_value.all.return_value = [mock_row]
    session.execute = AsyncMock(return_value=mock_result)

    experiences = await service.recall_agent_experience(task_type="sales", limit=5)
    assert len(experiences) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_collective_intelligence.py -v`
Expected: FAIL (方法不存在)

- [ ] **Step 3: 实现**

```python
# src/knowledge/memory.py — MemoryService 新增方法

async def store_agent_experience(
    self,
    employee_id: str,
    task_type: str,
    result_summary: str,
) -> Optional[Memory]:
    """Agent 执行成功后将经验写入共享知识库。"""
    try:
        memory = Memory(
            id=str(uuid4()),
            memory_type=MemoryType.LONG_TERM,
            content=f"[{task_type}] {result_summary}",
            metadata={"employee_id": employee_id, "task_type": task_type, "shared": True},
            created_at=datetime.now(UTC),
        )
        # 存储逻辑复用现有 MemoryService.store
        await self.store(memory)
        logger.info(f"Agent experience stored: employee={employee_id}, type={task_type}")
        return memory
    except Exception as e:
        logger.error(f"Failed to store agent experience: {e}")
        return None

async def recall_agent_experience(
    self,
    task_type: str,
    limit: int = 5,
) -> List[Memory]:
    """Agent 执行前检索同类经验。"""
    try:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Memory)
            .where(Memory.metadata["task_type"].as_string() == task_type)
            .where(Memory.metadata["shared"].as_boolean() == True)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.warning(f"Failed to recall agent experience: {e}")
        return []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_collective_intelligence.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/knowledge/memory.py tests/ai/test_collective_intelligence.py
git commit -m "feat: MemoryService 支持 Agent 经验存储与检索"
```

---

### Task 8: 执行链路注入经验共享

**Files:**
- Modify: `src/workforce/employee.py`
- Test: `tests/ai/test_collective_intelligence.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/ai/test_collective_intelligence.py — 追加

@pytest.mark.asyncio
async def test_low_trust_agent_cannot_access_shared_experience():
    """低信任 Agent 无法读取共享经验（准入控制）。"""
    # 信任评分低于阈值时 recall 返回空列表
    session = MagicMock()
    service = MemoryService(session)
    service.trust_threshold = 0.3

    # 模拟低信任 Agent
    experiences = await service.recall_agent_experience(
        task_type="sales",
        limit=5,
        requester_trust_score=0.1,  # 低于阈值
    )
    assert experiences == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ai/test_collective_intelligence.py::test_low_trust_agent_cannot_access_shared_experience -v`
Expected: FAIL (recall_agent_experience 不接受 requester_trust_score 参数)

- [ ] **Step 3: 实现**

修改 `recall_agent_experience` 增加准入控制参数，并在 `employee.py` 执行链路中注入调用。

```python
# src/knowledge/memory.py — 修改 recall_agent_experience 签名

async def recall_agent_experience(
    self,
    task_type: str,
    limit: int = 5,
    requester_trust_score: float = 1.0,
) -> List[Memory]:
    """Agent 执行前检索同类经验，低信任 Agent 被准入控制拦截。"""
    if requester_trust_score < getattr(self, "trust_threshold", 0.3):
        logger.info(f"Low trust ({requester_trust_score}) agent denied shared experience access")
        return []
    # ... 原有检索逻辑
```

```python
# src/workforce/employee.py — 在执行方法中注入经验共享
# 执行前检索同类经验注入 context
# 执行成功后写入经验
# 具体位置在 execute_task 方法中，依赖 AgentRouter.get_agent_trust_score 获取信任评分
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ai/test_collective_intelligence.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/knowledge/memory.py src/workforce/employee.py tests/ai/test_collective_intelligence.py
git commit -m "feat: 执行链路注入经验共享，低信任 Agent 准入控制"
```

---

### Task 9: 阶段 2 回归验证

- [ ] **Step 1: 运行完整回归测试**

Run: `python -m pytest -q`
Expected: 571+ passed, 0 failed

---

## 阶段 3：老板长期不在线（阶段 2 验证通过后）

### Task 10: 实现经营摘要报告生成

**Files:**
- Modify: `src/modules/ceo_dashboard_module.py`
- Test: `tests/modules/test_summary_report.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/modules/test_summary_report.py
import pytest
from unittest.mock import MagicMock
from src.modules.ceo_dashboard_module import CEODashboardModule


def test_summary_report_with_no_data():
    """无数据时报告中标注'数据不足'。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = MagicMock(return_value=MagicMock(fetchall=MagicMock(return_value=[])))

    report = module.generate_summary_report(session)
    assert report["status"] == "generated"
    assert "暂无" in report["goals"]["message"] or report["goals"]["count"] == 0
    assert "暂无" in report["alerts"]["message"] or len(report["alerts"]["items"]) == 0


def test_summary_report_structure():
    """报告结构完整。"""
    module = CEODashboardModule()
    session = MagicMock()

    report = module.generate_summary_report(session)
    assert "timestamp" in report
    assert "kpis" in report
    assert "alerts" in report
    assert "goals" in report
    assert "cost" in report
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/modules/test_summary_report.py -v`
Expected: FAIL (generate_summary_report 方法不存在)

- [ ] **Step 3: 实现**

```python
# src/modules/ceo_dashboard_module.py — 新增方法

def generate_summary_report(self, session) -> Dict[str, Any]:
    """生成经营摘要报告（按需触发，非离线调度）。

    聚合数据：
    - Dashboard 核心 KPI
    - 主动经营告警（scan_business_anomalies 输出）
    - Goal 执行状态和进度
    - AI 成本统计
    """
    now = datetime.now(UTC)
    report = {
        "timestamp": now.isoformat(),
        "status": "generated",
        "kpis": {"items": self._get_kpis_dict()},
        "alerts": {"items": [], "message": "暂无异常"},
        "goals": {"count": 0, "message": "暂无目标"},
        "cost": {"total_usd": 0.0, "message": "暂无成本数据"},
    }

    try:
        # 业务告警
        alerts = self.scan_business_anomalies(session)
        if alerts:
            report["alerts"] = {"items": alerts, "message": f"{len(alerts)} 条告警"}
    except Exception as e:
        logger.warning(f"Alert scan in report failed: {e}")

    try:
        # Goal 进度
        from sqlalchemy import text
        result = session.execute(text("SELECT COUNT(*) FROM goals")).fetchone()
        goal_count = result[0] if result else 0
        if goal_count > 0:
            report["goals"] = {"count": goal_count, "message": f"{goal_count} 个目标"}
    except Exception as e:
        logger.warning(f"Goal query in report failed: {e}")

    try:
        # 成本统计
        from sqlalchemy import text
        result = session.execute(text("SELECT COALESCE(SUM(cost_usd), 0) FROM ai_cost_records")).fetchone()
        total_cost = float(result[0]) if result else 0.0
        if total_cost > 0:
            report["cost"] = {"total_usd": total_cost, "message": f"${total_cost:.2f}"}
    except Exception as e:
        logger.warning(f"Cost query in report failed: {e}")

    return report
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/modules/test_summary_report.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/modules/ceo_dashboard_module.py tests/modules/test_summary_report.py
git commit -m "feat: 实现按需触发的经营摘要报告生成"
```

---

### Task 11: 最终回归验证

- [ ] **Step 1: 运行完整回归测试**

Run: `python -m pytest -q`
Expected: 571+ passed, 0 failed

- [ ] **Step 2: 运行 E2E 链路验证**

Run: `python -m pytest tests/integration/test_e2e_chain.py -v`
Expected: 5 passed

- [ ] **Step 3: 确认 Failure Recovery Chain 无回归**

检查失败恢复链相关测试全部通过，无新增失败。
