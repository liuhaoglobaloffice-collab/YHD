"""
Goal Service — 老板目标中心

持久化管理目标，连接 Parser → Planner → Workflow 完整链路。
"""

import structlog
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
from src.database.models import GoalModel, TaskModel
from src.identity.models import User

logger = structlog.get_logger(__name__)


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

    async def create_goal_from_text(
        self,
        text: str,
        user: Optional[User] = None,
        created_by: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> tuple:
        """
        P0-1 LLM 目标理解：老板一句自然语言 → 完整经营目标。

        链路：CEOCommandProcessor.parse_with_llm() → KPI/预算/时间/风险
        自动提取 → create_goal() 持久化。

        老板手动提供的字段优先（显式入参）；LLM 只补齐缺失字段。
        无可用 LLM Provider 时诚实降级为规则解析（字段留空，老板手填）。

        Returns:
            (GoalModel, Dict) — 目标 + 解析信息（parse_method / llm_error）
        """
        if not text or not text.strip():
            raise ValueError("目标文本不能为空")

        parsed: ParsedCommand = await self.parser.parse_with_llm(text)

        def _parse_date(value: Optional[str]):
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        goal = await self.create_goal(
            title=(parsed.goal or text)[:500],
            description=text,
            priority=parsed.priority.value,
            kpi_name=parsed.kpi_name,
            kpi_target=parsed.kpi_target,
            kpi_unit=parsed.kpi_unit,
            budget_total=parsed.budget_total,
            time_start=_parse_date(parsed.time_start),
            time_end=_parse_date(parsed.time_end),
            user=user,
            created_by=created_by,
            tenant_id=tenant_id,
        )

        # 解析来源记录进 plan_data（诚实标记 llm / rule_based）
        goal.plan_data = {
            "parse_method": parsed.metadata.get("parse_method", "rule_based"),
            "llm_error": parsed.metadata.get("llm_error"),
            "risk_boundaries": parsed.risk_boundaries,
            "constraints": parsed.constraints,
            "original_text": text,
        }
        await self.session.commit()
        await self.session.refresh(goal)

        parse_info = {
            "parse_method": parsed.metadata.get("parse_method", "rule_based"),
            "llm_error": parsed.metadata.get("llm_error"),
            "extracted": {
                "kpi_name": parsed.kpi_name,
                "kpi_target": parsed.kpi_target,
                "kpi_unit": parsed.kpi_unit,
                "budget_total": parsed.budget_total,
                "time_start": parsed.time_start,
                "time_end": parsed.time_end,
                "risk_boundaries": parsed.risk_boundaries,
            },
        }
        logger.info(
            f"Created goal from text: id={goal.id}, method={parse_info['parse_method']}"
        )
        return goal, parse_info

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

        # 创建 WorkflowExecutor 并执行，注入 TaskExecutor 确保任务真实执行
        from src.identity.audit import AuditService
        from src.identity.rbac import RBACService
        from src.tasks.executor import TaskExecutor
        from src.tasks.service import TaskService
        from src.workflow.service import WorkflowService
        from src.workforce.employee import AIEmployeeService
        from src.workforce.registry import AIEmployeeRegistry

        task_service = TaskService(self.session)
        rbac_service = RBACService(self.session)
        # TaskExecutor 必须注入 employee_service，否则任务无法由 AI 员工真实执行
        employee_service = AIEmployeeService(
            registry=AIEmployeeRegistry(self.session),
            rbac_service=rbac_service,
            audit_service=AuditService,
        )
        task_executor = TaskExecutor(
            task_service=task_service,
            employee_service=employee_service,
        )
        workflow_service = WorkflowService(self.session, rbac_service=rbac_service)
        executor = WorkflowExecutor(
            session=self.session,
            workflow_service=workflow_service,
            task_service=task_service,
            task_executor=task_executor,
            rbac_service=rbac_service,
        )
        execution = await executor.execute_workflow(
            workflow_id=wf_uuid,
            user=user,
            metadata={"goal_id": goal_id},
        )

        # 根据执行结果更新 Goal 状态
        from src.workflow.models import WorkflowExecutionStatus
        if execution.status == WorkflowExecutionStatus.COMPLETED:
            # 深检查：确保没有 Task 在 Workflow COMPLETED 时仍为 FAILED
            await self._verify_no_failed_tasks(workflow_id)
            goal.progress_pct = 100.0
            goal.status = "completed"
            goal.completed_at = datetime.now(UTC)
            if goal.plan_data:
                # JSON 列原地修改不触发 SQLAlchemy 变更检测，必须整体重新赋值
                updated_plan = dict(goal.plan_data)
                updated_plan["execution_result"] = {
                    "execution_id": str(execution.execution_id),
                    "status": "completed",
                    "result": execution.result,
                }
                goal.plan_data = updated_plan
        elif execution.status == WorkflowExecutionStatus.FAILED:
            goal.status = "failed"
            if goal.plan_data:
                updated_plan = dict(goal.plan_data)
                updated_plan["execution_result"] = {
                    "execution_id": str(execution.execution_id),
                    "status": "failed",
                    "error": execution.error,
                }
                updated_plan["failure_reason"] = execution.error
                goal.plan_data = updated_plan
        else:
            # 还在运行中，只更新进度
            goal.progress_pct = 50.0

        # 记账（必须放在状态判定之后，避免被 completed 的 100% 覆盖）：
        # 进度按任务真实完成情况计算，预算按该目标链路的真实 AI 调用花费汇总，
        # KPI 只统计可核实的真实业务结果，绝不伪造数字。
        try:
            await self._settle_goal_after_execution(goal_id, str(workflow_id))
        except Exception as settle_err:
            logger.error(f"goal_settlement_failed: goal_id={goal_id}, error={settle_err}", exc_info=True)

        await self.session.commit()
        await self.session.refresh(goal)

        logger.info(
            f"Executed goal workflow: id={goal_id}, "
            f"workflow_status={execution.status.value}, "
            f"goal_status={goal.status}"
        )
        return goal

    async def _settle_goal_after_execution(self, goal_id: int, workflow_id: str) -> None:
        """
        目标执行结算：把"跑过"变成"记下来"。

        - progress_pct：按该目标下任务的真实完成比例计算（completed / 全部）
        - budget_spent：汇总该目标链路中**真实发生**的 AI 调用成本（ai_cost_records）
        - kpi_current：只统计可核实的真实业务结果；无法核实的 KPI 保持原值并记录待接入原因，
          绝不返回编造数字

        幂等：可重复调用，数值为全量重算而非累加。
        """
        goal = await self.session.get(GoalModel, goal_id)
        if not goal:
            return

        # 1. 任务完成情况
        task_rows = (
            await self.session.execute(
                select(TaskModel.status).where(TaskModel.workflow_id == workflow_id)
            )
        ).scalars().all()
        total_tasks = len(task_rows)
        completed_tasks = sum(1 for s in task_rows if s == "completed")
        failed_tasks = sum(1 for s in task_rows if s == "failed")

        if total_tasks:
            goal.progress_pct = round(completed_tasks / total_tasks * 100.0, 1)

        # 2. 真实 AI 调用成本（按 task_id 归集本目标链路的记录）
        task_ids = {
            str(r[0])
            for r in (
                await self.session.execute(
                    select(TaskModel.id).where(TaskModel.workflow_id == workflow_id)
                )
            ).all()
        }
        spent = 0.0
        tokens = 0
        calls = 0
        if task_ids:
            try:
                from src.database.models import AiCostRecordModel

                since = goal.time_start or goal.created_at
                cost_rows = (
                    await self.session.execute(
                        select(AiCostRecordModel).where(
                            AiCostRecordModel.created_at >= since
                        )
                    )
                ).scalars().all()
                for rec in cost_rows:
                    meta = rec.meta or {}
                    if str(meta.get("task_id")) in task_ids:
                        spent += float(rec.cost_usd or 0.0)
                        tokens += int(rec.total_tokens or 0)
                        calls += 1
            except Exception as cost_err:
                logger.warning(f"goal_cost_aggregation_failed: goal_id={goal_id}, error={cost_err}")

        goal.budget_spent = round(spent, 6)

        # 3. KPI：仅采集可核实的真实结果
        kpi_note = None
        kpi_name = (goal.kpi_name or "").lower()
        kpi_value = None
        if any(k in kpi_name for k in ("线索", "潜在客户", "客户数", "lead", "customer")):
            try:
                from src.crm.models import Lead

                since = goal.time_start or goal.created_at
                kpi_value = float(
                    (
                        await self.session.execute(
                            select(func.count()).select_from(Lead).where(
                                Lead.created_at >= since
                            )
                        )
                    ).scalar_one()
                )
            except Exception:
                kpi_note = "KPI 采集器暂不可用（线索表读取失败）"
        else:
            kpi_note = "该 KPI 暂无自动采集器，需接入真实业务数据源后自动回写"

        if kpi_value is not None:
            goal.kpi_current = kpi_value
        elif kpi_note and goal.kpi_current == 0:
            kpi_note = kpi_note

        # 4. 结算快照写入 plan_data，供前端与汇报消费
        updated_plan = dict(goal.plan_data or {})
        updated_plan["settlement"] = {
            "tasks_total": total_tasks,
            "tasks_completed": completed_tasks,
            "tasks_failed": failed_tasks,
            "ai_calls": calls,
            "tokens_used": tokens,
            "cost_usd": round(spent, 6),
            "cost_note": (
                "本地 Ollama 无 API 费用，成本计为 0；Token 消耗为真实计量"
                if spent == 0 and tokens
                else None
            ),
            "kpi_note": kpi_note,
            "settled_at": datetime.now(UTC).isoformat(),
        }
        goal.plan_data = updated_plan

        logger.info(
            f"goal_settled: goal_id={goal_id}, progress_pct={goal.progress_pct}, "
            f"tasks={completed_tasks}/{total_tasks}, tokens={tokens}, "
            f"cost_usd={round(spent, 6)}, kpi_current={goal.kpi_current}"
        )

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
        if goal.status in ("completed", "cancelled", "failed"):
            raise ValueError(f"目标已经是终态，不允许回退: {goal.status}")
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
        if goal.status in ("completed", "cancelled", "failed"):
            raise ValueError(f"目标已经是终态，不允许取消: {goal.status}")
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

    async def _verify_no_failed_tasks(self, workflow_id: str) -> None:
        """深检查：Workflow COMPLETED 时确保没有 Task 为 FAILED 状态。"""
        from sqlalchemy import select
        query = select(TaskModel).where(
            TaskModel.workflow_id == workflow_id,
            TaskModel.status == "failed",
        )
        result = await self.session.execute(query)
        failed_tasks = list(result.scalars().all())
        if failed_tasks:
            logger.error(
                "goal_workflow_inconsistent_state",
                workflow_id=workflow_id,
                failed_task_count=len(failed_tasks),
                failed_task_ids=[t.id for t in failed_tasks],
            )
            raise RuntimeError(
                f"Workflow COMPLETED but {len(failed_tasks)} task(s) are FAILED. "
                "State inconsistency detected — goal cannot be marked completed."
            )

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