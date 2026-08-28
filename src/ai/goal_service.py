"""
Goal Service — 老板目标中心

持久化管理目标，连接 Parser → Planner → Workflow 完整链路。
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agent_router import AgentRouter
from src.ai.command_processor import CEOCommandProcessor
from src.ai.models import ParsedCommand
from src.ai.planner import IntelligentPlanner
from src.ai.workflow_bridge import WorkflowBridge
from src.database.models import GoalModel, FailureRecordModel
from src.identity.models import User

logger = logging.getLogger(__name__)


class GoalService:
    """目标管理服务 — 创建、跟踪、完成目标。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.parser = CEOCommandProcessor()
        self.planner = IntelligentPlanner()
        self.agent_router = AgentRouter(session)
        self.workflow_bridge = WorkflowBridge(session)

    async def create_goal(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "normal",
        kpi_name: Optional[str] = None,
        kpi_target: Optional[float] = None,
        kpi_unit: Optional[str] = None,
        budget_total: Optional[float] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        user: Optional[User] = None,
        created_by: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> GoalModel:
        """创建新目标。"""
        goal = GoalModel(
            title=title,
            description=description,
            priority=priority,
            status="draft",
            kpi_name=kpi_name,
            kpi_target=kpi_target,
            kpi_unit=kpi_unit,
            budget_total=budget_total,
            budget_spent=0.0,
            time_start=time_start,
            time_end=time_end,
            progress_pct=0.0,
            created_by=created_by or (user.id if user else 0),
            tenant_id=tenant_id or (getattr(user, "tenant_id", None) if user else None),
        )
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)
        logger.info(f"Created goal: id={goal.id}, title='{title}'")
        return goal

    async def activate_goal(self, goal_id: int, user: User) -> GoalModel:
        """激活目标：解析 → 规划 → 路由 Agent → 生成 Workflow。"""
        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            raise ValueError("目标不存在")
        if goal.status != "draft":
            raise ValueError(f"目标状态不允许激活: {goal.status}")

        # Step 1: 解析目标（Parser）
        parsed: ParsedCommand = self.parser.parse(
            f"{goal.title}。{goal.description or ''}",
            context={"goal_id": goal.id, "kpi": goal.kpi_name, "budget": goal.budget_total},
        )

        # Step 2: 规划任务（Planner）
        plan = self.planner.create_plan(parsed)

        # Step 3: 路由任务到 AI 员工（Agent Router）
        assignments = await self.agent_router.route_tasks(plan)

        # Step 4: 创建 Workflow（Workflow Bridge）
        workflow = await self.workflow_bridge.create_workflow_from_plan(
            plan=plan,
            assignments=assignments,
            user=user,
        )

        # Step 5: 存储计划 & 关联 Workflow
        goal.plan_data = {
            "goal": plan.goal,
            "tasks": plan.tasks,
            "execution_order": plan.execution_order,
            "estimated_duration_minutes": plan.estimated_duration_minutes,
            "dependencies": plan.dependencies,
            "parsed_command": {
                "constraints": parsed.constraints,
                "priority": parsed.priority.value,
                "required_agents": parsed.required_agents,
            },
            "agent_assignments": [
                {
                    "task_id": str(a.task_id),
                    "agent_type": a.agent_type,
                    "employee_id": str(a.employee_id) if a.employee_id else None,
                    "employee_name": a.employee_name,
                }
                for a in assignments
            ],
        }
        goal.workflow_id = str(workflow.workflow_id)
        goal.status = "active"
        goal.time_start = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(goal)

        logger.info(
            f"Activated goal: id={goal_id}, tasks={len(plan.tasks)}, "
            f"workflow_id={workflow.workflow_id}"
        )
        return goal

    async def execute_goal_workflow(self, goal_id: int, user: User) -> GoalModel:
        """执行目标关联的 Workflow：执行 → 更新 Goal 状态。"""
        from src.workflow.executor import WorkflowExecutor

        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            raise ValueError("目标不存在")
        if goal.status != "active":
            raise ValueError(f"目标状态不允许执行: {goal.status}")
        if not goal.workflow_id:
            raise ValueError("目标尚未关联 Workflow，请先激活")

        workflow_id = goal.workflow_id
        from uuid import UUID
        wf_uuid = UUID(workflow_id)

        # 创建 WorkflowExecutor 并执行
        executor = WorkflowExecutor(session=self.session)
        execution = await executor.execute_workflow(
            workflow_id=wf_uuid,
            user=user,
            metadata={"goal_id": goal_id},
        )

        # 根据执行结果更新 Goal 状态
        from src.workflow.models import WorkflowExecutionStatus
        if execution.status == WorkflowExecutionStatus.COMPLETED:
            goal.progress_pct = 100.0
            goal.status = "completed"
            goal.completed_at = datetime.now(UTC)
            if goal.plan_data:
                goal.plan_data["execution_result"] = {
                    "execution_id": str(execution.execution_id),
                    "status": "completed",
                    "result": execution.result,
                }
        elif execution.status == WorkflowExecutionStatus.FAILED:
            goal.status = "failed"
            if goal.plan_data:
                goal.plan_data["execution_result"] = {
                    "execution_id": str(execution.execution_id),
                    "status": "failed",
                    "error": execution.error,
                }
            if goal.plan_data:
                goal.plan_data["failure_reason"] = execution.error
        else:
            # 还在运行中，只更新进度
            goal.progress_pct = 50.0

        await self.session.commit()
        await self.session.refresh(goal)

        logger.info(
            f"Executed goal workflow: id={goal_id}, "
            f"workflow_status={execution.status.value}, "
            f"goal_status={goal.status}"
        )
        return goal

    async def update_progress(
        self, goal_id: int, progress_pct: float, kpi_current: Optional[float] = None
    ) -> GoalModel:
        """更新目标进度。"""
        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            raise ValueError("目标不存在")
        goal.progress_pct = max(0.0, min(100.0, progress_pct))
        if kpi_current is not None:
            goal.kpi_current = kpi_current
        if progress_pct >= 100.0:
            goal.status = "completed"
            goal.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def complete_goal(self, goal_id: int) -> GoalModel:
        """完成目标。"""
        return await self.update_progress(goal_id, 100.0)

    async def fail_goal(self, goal_id: int, reason: str) -> GoalModel:
        """标记目标失败。"""
        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            raise ValueError("目标不存在")
        goal.status = "failed"
        if goal.plan_data:
            goal.plan_data["failure_reason"] = reason
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def cancel_goal(self, goal_id: int) -> GoalModel:
        """取消目标。"""
        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            raise ValueError("目标不存在")
        goal.status = "cancelled"
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def get_goal(self, goal_id: int) -> Optional[GoalModel]:
        """获取单个目标。"""
        return await self.session.get(GoalModel, goal_id)

    async def list_goals(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        created_by: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取目标列表（分页、筛选）。"""
        query = select(GoalModel)
        if status:
            query = query.where(GoalModel.status == status)
        if priority:
            query = query.where(GoalModel.priority == priority)
        if created_by:
            query = query.where(GoalModel.created_by == created_by)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one() or 0

        query = query.order_by(desc(GoalModel.updated_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.execute(query)).scalars().all())

        return {
            "items": [self._to_dict(g) for g in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _to_dict(self, goal: GoalModel) -> Dict[str, Any]:
        return {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "status": goal.status,
            "priority": goal.priority,
            "kpi_name": goal.kpi_name,
            "kpi_target": goal.kpi_target,
            "kpi_current": goal.kpi_current,
            "kpi_unit": goal.kpi_unit,
            "budget_total": goal.budget_total,
            "budget_spent": goal.budget_spent,
            "time_start": goal.time_start.isoformat() if goal.time_start else None,
            "time_end": goal.time_end.isoformat() if goal.time_end else None,
            "plan_data": goal.plan_data,
            "workflow_id": goal.workflow_id,
            "progress_pct": goal.progress_pct,
            "created_by": goal.created_by,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
            "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        }