"""
Agent Router - Phase 3.1 AI Brain Core

Routes tasks to appropriate AI agents/employees.
"""

import logging
from datetime import UTC, datetime
from typing import Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..workforce.models import AIEmployeeStatus, Department, Position
from ..workforce.registry import AIEmployeeRegistry
from .models import AgentAssignment, TaskDecomposition

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Routes tasks to appropriate AI agents/employees.

    Responsibilities:
    - Map task types to agent types
    - Select best available agent/employee
    - Load balancing (future)
    - Fallback selection
    """

    # Agent type to Department/Position mapping
    AGENT_MAPPING = {
        "research": {
            "department": Department.RESEARCH,
            "position": Position.MARKET_RESEARCHER,
        },
        "marketing": {
            "department": Department.MARKETING,
            "position": Position.MARKETING_SPECIALIST,
        },
        "sales": {
            "department": Department.SALES,
            "position": Position.SALES_REPRESENTATIVE,
        },
        "business": {
            "department": Department.OPERATIONS,
            "position": Position.OPERATIONS_COORDINATOR,
        },
        "ceo_assistant": {
            "department": Department.CEO_OFFICE,
            "position": Position.CEO_ASSISTANT,
        },
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = AIEmployeeRegistry(session)
        logger.info("AgentRouter initialized")

    async def route_tasks(self, plan: TaskDecomposition) -> List[AgentAssignment]:
        """
        Route all tasks in plan to specific AI employees.

        Args:
            plan: Task decomposition plan

        Returns:
            List of agent assignments
        """
        assignments = []

        for task in plan.tasks:
            assignment = await self.route_task(task)
            assignments.append(assignment)

        logger.info(f"Routed {len(assignments)} tasks to agents")

        return assignments

    async def route_task(self, task: Dict) -> AgentAssignment:
        """
        Route single task to specific AI employee, sorted by trust score.

        低信任评分（<0.3）的员工被自动降权跳过。
        """
        agent_type = task.get('agent_type', 'business')
        task_id = UUID(task['task_id'])

        mapping = self.AGENT_MAPPING.get(agent_type, self.AGENT_MAPPING['business'])

        try:
            employees = await self.registry.list_employees(
                department=mapping['department'], status=AIEmployeeStatus.ACTIVE
            )

            if employees:
                TRUST_THRESHOLD = 0.3
                scored = []
                for emp in employees:
                    trust = await self.get_agent_trust_score(str(emp.id))
                    if trust >= TRUST_THRESHOLD:
                        scored.append((emp, trust))

                if not scored:
                    scored = []
                    for emp in employees:
                        trust = await self.get_agent_trust_score(str(emp.id))
                        scored.append((emp, trust))
                    logger.warning(
                        f'All employees below trust threshold {TRUST_THRESHOLD} '
                        f'for task {task.get("name", "unknown")}'
                    )

                scored.sort(key=lambda x: x[1], reverse=True)
                employee, trust_score = scored[0]

                assignment = AgentAssignment(
                    task_id=task_id,
                    task_description=task.get('description', task['name']),
                    agent_type=agent_type,
                    employee_id=employee.id,
                    employee_name=employee.name,
                    department=employee.department.value,
                    position=employee.position.value,
                    confidence=trust_score,
                    reason=f'Selected {employee.name} (trust={trust_score:.2f})',
                )
            else:
                error_msg = (
                    f'No {agent_type} AI employee available for task {task.get("name", "unknown")}. '
                    'Register an AI employee with the required department/position before activating goals.'
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            logger.error(f'Error routing task {task_id}: {e}')
            raise ValueError(f'Failed to route task {task.get("name", "unknown")}: {e}') from e

        return assignment

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

    async def get_agent_risk_score(self, employee_id: str) -> float:
        """
        基于失败恢复记录计算风险评分。

        通过 tasks.assigned_to 关联 FailureRecordModel，
        统计未恢复失败比例。无记录时返回 0.1（低风险默认）。

        注意：assigned_to 是 JSON 列表列。不能对 JSON 列使用 LIKE
        （SQLite 把 JSON 存成 TEXT 可以工作，但 PostgreSQL 上
        ``json LIKE text`` 会直接报错并中止整个事务，污染后续所有
        查询）。因此这里用 ORM 取出后在 Python 侧过滤，跨数据库安全。
        """
        from sqlalchemy import select
        from ..database.models import FailureRecordModel, TaskModel

        try:
            task_rows = (
                await self.session.execute(
                    select(TaskModel.id, TaskModel.assigned_to)
                )
            ).all()
            task_ids = [
                str(tid)
                for tid, assigned in task_rows
                if assigned
                and isinstance(assigned, list)
                and employee_id in {str(a) for a in assigned}
            ]
            if not task_ids:
                return 0.1

            rows = (
                await self.session.execute(
                    select(FailureRecordModel.is_successful).where(
                        FailureRecordModel.task_id.in_(task_ids)
                    )
                )
            ).all()
            total = len(rows)
            if total == 0:
                return 0.1
            unrecovered = sum(1 for (is_successful,) in rows if not is_successful)
            return min(unrecovered / total, 1.0)
        except Exception as e:
            logger.warning(f"Failed to get risk score for {employee_id}: {e}")
            return 0.5

    async def get_agent_trust_score(self, employee_id: str) -> float:
        """
        综合信任评分 = 能力(40%) + 风险(30%) + 权限范围(30%)。

        - 能力: get_agent_capability_score (success_rate)
        - 风险: 1 - get_agent_risk_score (低风险 = 高信任)
        - 权限范围: 基于 RBAC 权限数量归一化（默认 0.5）

        P1-G2.2: 若存在手动 override（ai_employees.meta.trust_override），
        优先返回手动值（老板干预优先于动态计算）。
        """
        # 手动 override 优先（查询失败时诚实降级到动态计算，不阻塞路由）
        try:
            override = await self._load_trust_override(employee_id)
            if override is not None:
                return float(override["score"])
        except Exception as e:
            logger.warning(f"Failed to load trust override for {employee_id}: {e}")

        capability = await self.get_agent_capability_score(employee_id)
        risk = await self.get_agent_risk_score(employee_id)

        # 权限范围评分：当前简化为 0.5（后续可从 RBAC 查询权限数量归一化）
        permission_score = 0.5

        trust = (capability * 0.4) + ((1.0 - risk) * 0.3) + (permission_score * 0.3)
        return round(min(max(trust, 0.0), 1.0), 4)

    # ==================================================================
    # P1-G2.2: 手动信任 override（老板干预）— 持久化到 ai_employees.meta
    # ==================================================================

    async def _load_trust_override(self, employee_id: str):
        """读取 ai_employees.meta 中的 trust_override；不存在返回 None。"""
        from ..database.models import AIEmployeeModel

        emp = await self.session.get(AIEmployeeModel, employee_id)
        if emp is None:
            return None
        return (emp.meta or {}).get("trust_override")

    async def set_trust_override(
        self,
        employee_id: str,
        score: float,
        reason: str,
        actor_id: int,
    ) -> dict:
        """手动设置信任评分 override（持久化到 ai_employees.meta）。

        - score 必须在 [0,1] 区间，否则 ValueError（fail-closed）
        - override 数据含 override_source=MANUAL / actor_id / reason / set_at，
          满足"可追溯、不伪装动态计算"的诚实要求
        """
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"trust override score must be in [0,1], got {score}")

        from ..database.models import AIEmployeeModel

        emp = await self.session.get(AIEmployeeModel, employee_id)
        if emp is None:
            raise ValueError(f"AI employee {employee_id} not found")

        meta = dict(emp.meta or {})
        meta["trust_override"] = {
            "score": float(score),
            "reason": reason,
            "override_source": "MANUAL",
            "actor_id": actor_id,
            "set_at": datetime.now(UTC).isoformat(),
        }
        emp.meta = meta
        await self.session.commit()
        logger.info(
            f"Trust override set: employee={employee_id}, score={score}, actor={actor_id}"
        )
        return meta["trust_override"]

    async def clear_trust_override(self, employee_id: str) -> bool:
        """清除手动 override，恢复动态信任计算。

        返回 True 表示清除成功；员工不存在时抛 ValueError。
        """
        from ..database.models import AIEmployeeModel

        emp = await self.session.get(AIEmployeeModel, employee_id)
        if emp is None:
            raise ValueError(f"AI employee {employee_id} not found")

        meta = dict(emp.meta or {})
        if "trust_override" not in meta:
            return False
        del meta["trust_override"]
        emp.meta = meta
        await self.session.commit()
        logger.info(f"Trust override cleared: employee={employee_id}")
        return True
