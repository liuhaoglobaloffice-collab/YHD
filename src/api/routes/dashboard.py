"""
Dashboard API Routes
CEO 仪表板数据接口
"""

from typing import Dict, List
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.business.supplier.models import Supplier, SupplierStatus, BusinessType
from src.database.models import AIEmployeeModel, TaskModel
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/live-activity")
async def get_live_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 12,
) -> Dict:
    """
    全站「AI 正在工作」实时活动源（Y1.0）。

    一次请求返回所有核心页面需要的真实数据（全部来自数据库，非伪造）：
    - employees: AI 员工在岗状态（含 provider/model）
    - recent_tasks: 最近任务执行（含成败与执行摘要）
    - running: 执行中任务数 / 工作流
    - workflows: 最近工作流执行状态
    - goals: 目标进度（含结算后的 progress/kpi/budget）
    - model_calls: 最近模型调用（provider/model/token/成败）
    - knowledge: 知识库文档数 + 最近记忆活动
    - audit: 最近审计事件

    前端 Layout 全局轮询此接口，使任何页面都能看到「系统正在工作」。
    """
    from src.database.models import (
        AgentMemoryModel,
        DocumentModel,
        GoalModel,
        WorkflowExecutionModel,
        WorkflowModel,
    )
    from src.database.models import AiCostRecordModel
    from src.identity.models import AuditLog

    limit = max(1, min(limit, 30))
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _first_assignee(assigned_to) -> str | None:
        """assigned_to 是 JSON 列表列（List[agent_id]），取第一个负责人。"""
        if not assigned_to:
            return None
        if isinstance(assigned_to, list):
            return str(assigned_to[0]) if assigned_to else None
        return str(assigned_to)

    def _task_summary(result_data) -> str:
        """从真实 result_data 提取执行结果摘要（不伪造）。"""
        if not result_data:
            return ""
        if isinstance(result_data, dict):
            out = result_data.get("output") or result_data.get("result") or result_data.get("summary") or ""
            if out:
                return str(out)[:120]
            # 结构化结果（如线索/报价数量）尽量给出真实数字
            for key in ("leads_count", "count", "total", "quotes_count"):
                if result_data.get(key) is not None:
                    return f"{key}={result_data.get(key)}"
        return str(result_data)[:120]

    def _real_progress(task) -> float | None:
        """仅当任务/结果中真实记录了进度时返回百分比，否则 None（前端显示不确定态，不伪造）。"""
        for container in (getattr(task, "meta", None), getattr(task, "result_data", None)):
            if isinstance(container, dict):
                p = container.get("progress") or container.get("progress_pct")
                if isinstance(p, (int, float)) and 0 <= p <= 100:
                    return float(p)
        return None

    def _real_step(task) -> str | None:
        """仅当任务/结果中真实记录了当前步骤时返回。"""
        for container in (getattr(task, "meta", None), getattr(task, "result_data", None)):
            if isinstance(container, dict):
                step = container.get("current_step") or container.get("step")
                if step:
                    return str(step)[:120]
        return None

    # 1. AI 员工
    emp_rows = (
        await db.execute(
            select(
                AIEmployeeModel.id,
                AIEmployeeModel.name,
                AIEmployeeModel.position,
                AIEmployeeModel.department,
                AIEmployeeModel.status,
                AIEmployeeModel.provider,
                AIEmployeeModel.model,
                AIEmployeeModel.updated_at,
            ).order_by(AIEmployeeModel.updated_at.desc())
        )
    ).all()
    employees = [
        {
            "id": str(r.id),
            "name": r.name,
            "position": r.position,
            "department": r.department,
            "status": r.status,
            "provider": r.provider,
            "model": r.model,
        }
        for r in emp_rows
    ]
    active_employees = sum(1 for e in employees if e["status"] == "active")
    emp_by_id = {e["id"]: e for e in employees}
    emp_name_by_id = {e["id"]: e["name"] for e in employees}

    # 1b. 工作流定义名称表
    wf_def_rows = (
        await db.execute(select(WorkflowModel.id, WorkflowModel.name))
    ).all()
    wf_name_by_id = {str(r.id): r.name for r in wf_def_rows}

    # 1c. 目标表（goal 通过 workflow_id 与 workflow/task 关联）
    goal_all_rows = (
        await db.execute(
            select(
                GoalModel.id,
                GoalModel.title,
                GoalModel.status,
                GoalModel.progress_pct,
                GoalModel.workflow_id,
                GoalModel.kpi_name,
                GoalModel.kpi_current,
                GoalModel.kpi_target,
                GoalModel.budget_total,
                GoalModel.budget_spent,
                GoalModel.updated_at,
            ).order_by(GoalModel.updated_at.desc())
        )
    ).all()
    goal_by_wf: Dict[str, object] = {}
    goals = []
    for r in goal_all_rows:
        g = {
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "progress_pct": r.progress_pct,
            "kpi_name": r.kpi_name,
            "kpi_current": r.kpi_current,
            "kpi_target": r.kpi_target,
            "budget_total": r.budget_total,
            "budget_spent": r.budget_spent,
            "workflow_id": str(r.workflow_id) if r.workflow_id else None,
        }
        goals.append(g)
        if r.workflow_id and str(r.workflow_id) not in goal_by_wf:
            goal_by_wf[str(r.workflow_id)] = g

    def _goal_for_workflow(workflow_id):
        if not workflow_id:
            return None
        return goal_by_wf.get(str(workflow_id))

    # 2. 最近任务（含成败摘要 + 员工/目标/工作流关联）
    task_rows = (
        await db.execute(
            select(TaskModel)
            .order_by(TaskModel.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    recent_tasks = []
    for r in task_rows:
        assignee_id = _first_assignee(r.assigned_to)
        emp = emp_by_id.get(assignee_id) if assignee_id else None
        goal = _goal_for_workflow(r.workflow_id)
        recent_tasks.append({
            "id": str(r.id),
            "title": r.title,
            "status": r.status,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "summary": _task_summary(r.result_data),
            "error": (r.error or "")[:160] if r.error else None,
            "employee_id": assignee_id,
            "employee_name": (emp or {}).get("name") if emp else None,
            "provider": (emp or {}).get("provider") if emp else None,
            "model": (emp or {}).get("model") if emp else None,
            "workflow_id": str(r.workflow_id) if r.workflow_id else None,
            "workflow_name": wf_name_by_id.get(str(r.workflow_id)) if r.workflow_id else None,
            "goal_id": (goal or {}).get("id") if goal else None,
            "goal_title": (goal or {}).get("title") if goal else None,
        })

    running_task_count = (
        await db.execute(select(func.count(TaskModel.id)).where(TaskModel.status == "running"))
    ).scalar() or 0

    # 2b. 今日任务统计（真实时间窗，UTC 当日）
    async def _count_today(status: str) -> int:
        c = (
            await db.execute(
                select(func.count(TaskModel.id)).where(
                    TaskModel.status == status,
                    func.coalesce(TaskModel.completed_at, TaskModel.updated_at) >= today_start,
                )
            )
        ).scalar()
        return int(c or 0)

    completed_today = await _count_today("completed")
    failed_today = await _count_today("failed")

    # 2c. 「AI 正在工作」：运行中的任务（真实 Execution 数据，无伪造进度）
    from sqlalchemy import nulls_last
    running_rows = (
        await db.execute(
            select(TaskModel)
            .where(TaskModel.status == "running")
            .order_by(nulls_last(TaskModel.started_at.desc()))
            .limit(10)
        )
    ).scalars().all()
    working_now = []
    for r in running_rows:
        assignee_id = _first_assignee(r.assigned_to)
        emp = emp_by_id.get(assignee_id) if assignee_id else None
        goal = _goal_for_workflow(r.workflow_id)
        working_now.append({
            "kind": "task",
            "id": str(r.id),
            "title": r.title,
            "status": "running",
            "employee_id": assignee_id,
            "employee_name": (emp or {}).get("name") if emp else None,
            "position": (emp or {}).get("position") if emp else None,
            "provider": (emp or {}).get("provider") if emp else None,
            "model": (emp or {}).get("model") if emp else None,
            "goal_id": (goal or {}).get("id") if goal else None,
            "goal_title": (goal or {}).get("title") if goal else None,
            "goal_progress": (goal or {}).get("progress_pct") if goal else None,
            "workflow_id": str(r.workflow_id) if r.workflow_id else None,
            "workflow_name": wf_name_by_id.get(str(r.workflow_id)) if r.workflow_id else None,
            "current_step": _real_step(r),
            "progress": _real_progress(r),
            "started_at": r.started_at.isoformat() if r.started_at else (r.updated_at.isoformat() if r.updated_at else None),
        })

    # 3. 最近工作流执行 + 运行中的工作流
    wf_rows = (
        await db.execute(
            select(WorkflowExecutionModel)
            .order_by(nulls_last(WorkflowExecutionModel.started_at.desc()))
            .limit(8)
        )
    ).scalars().all()
    workflows = []
    for r in wf_rows:
        wf_status = (r.status or "").lower()
        goal = _goal_for_workflow(r.workflow_id)
        item = {
            "execution_id": str(r.id),
            "workflow_id": str(r.workflow_id) if r.workflow_id else None,
            "workflow_name": wf_name_by_id.get(str(r.workflow_id)) if r.workflow_id else None,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error": (r.error or "")[:160] if r.error else None,
            "goal_id": (goal or {}).get("id") if goal else None,
            "goal_title": (goal or {}).get("title") if goal else None,
        }
        workflows.append(item)
        if wf_status == "running":
            working_now.append({
                "kind": "workflow",
                "id": str(r.id),
                "title": wf_name_by_id.get(str(r.workflow_id), f"工作流 {str(r.workflow_id)[:8]}") if r.workflow_id else "工作流执行",
                "status": "running",
                "employee_name": None,
                "provider": None,
                "model": None,
                "goal_id": (goal or {}).get("id") if goal else None,
                "goal_title": (goal or {}).get("title") if goal else None,
                "goal_progress": (goal or {}).get("progress_pct") if goal else None,
                "workflow_id": str(r.workflow_id) if r.workflow_id else None,
                "workflow_name": wf_name_by_id.get(str(r.workflow_id)) if r.workflow_id else None,
                "current_step": None,
                "progress": (goal or {}).get("progress_pct") if goal else None,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "execution_id": str(r.id),
            })

    # 3b. 阻塞中任务（等待审批/人工介入）
    blocked_count = (
        await db.execute(select(func.count(TaskModel.id)).where(TaskModel.status == "blocked"))
    ).scalar() or 0
    failed_count = (
        await db.execute(select(func.count(TaskModel.id)).where(TaskModel.status == "failed"))
    ).scalar() or 0

    # 4. 「AI CEO 建议」——全部由真实信号派生，无信号时返回空列表（前端显示无待办）
    recommendations: List[Dict] = []

    # 4a. 失败任务 → 建议重新调度（真实失败记录）
    failed_tasks_rows = (
        await db.execute(
            select(TaskModel)
            .where(TaskModel.status == "failed")
            .order_by(TaskModel.updated_at.desc())
            .limit(3)
        )
    ).scalars().all()
    for t in failed_tasks_rows:
        assignee_id = _first_assignee(t.assigned_to)
        emp_name = emp_name_by_id.get(assignee_id) if assignee_id else None
        recommendations.append({
            "id": f"rec-task-failed-{t.id}",
            "type": "task_failed",
            "priority": "high",
            "title": f"任务执行失败：{t.title}",
            "problem": (t.error or "任务执行未成功完成")[:160],
            "impact": f"该任务由 {emp_name or 'AI 员工'} 执行，失败会阻塞相关业务目标推进。",
            "analysis": "Failure Recovery Chain 已记录本次失败。建议查看失败原因，确认是模型/网络问题还是业务逻辑问题后重新调度。",
            "suggestion": "查看执行详情，确认原因后重新调度任务。",
            "action_label": "查看并处理",
            "action_url": f"/workflow?task={t.id}",
            "created_at": (t.updated_at or now).isoformat() if t.updated_at else now.isoformat(),
        })

    # 4b. 阻塞任务 → 等待审批/人工介入
    if blocked_count > 0:
        recommendations.append({
            "id": "rec-task-blocked",
            "type": "task_blocked",
            "priority": "high",
            "title": f"{blocked_count} 个任务阻塞，等待处理",
            "problem": f"当前有 {blocked_count} 个任务处于 blocked 状态，可能等待审批或人工决策。",
            "impact": "阻塞任务会导致对应工作流无法继续，影响目标交付时效。",
            "analysis": "阻塞通常意味着需要人工审批或外部输入。请在审批队列中查看待办事项。",
            "suggestion": "前往审批队列处理阻塞项。",
            "action_label": "前往审批",
            "action_url": "/approvals",
            "created_at": now.isoformat(),
        })

    # 4c. 业务异常（线索下降/客户流失/供应商高风险，来自真实业务数据扫描）
    try:
        from src.modules.ceo_dashboard_module import CEODashboardModule

        anomaly_alerts = await CEODashboardModule().scan_business_anomalies(db)
        action_map = {
            "lead_decline": ("/leads", "查看线索"),
            "customer_churn": ("/leads", "查看客户"),
            "supplier_risk_change": ("/supplier-analysis", "查看供应商风险"),
        }
        for a in anomaly_alerts:
            url, label = action_map.get(a.get("type"), ("/metrics", "查看详情"))
            recommendations.append({
                "id": f"rec-{a.get('id', a.get('type'))}",
                "type": a.get("type", "business_anomaly"),
                "priority": "high" if a.get("level") == "critical" else "medium",
                "title": a.get("title", "业务异常"),
                "problem": a.get("message", "")[:160],
                "impact": "该异常可能影响业务目标达成，建议及时关注。",
                "analysis": "由 CEO 经营异常扫描基于真实业务数据检测得出。",
                "suggestion": "进入对应业务页面核实并采取行动。",
                "action_label": label,
                "action_url": url,
                "created_at": a.get("timestamp") or now.isoformat(),
            })
    except Exception as e:
        logger.warning("dashboard_recommendations_anomaly_scan_failed", error=str(e))

    # 4d. 团队尚未配置 → 引导上手
    if len(employees) == 0:
        recommendations.append({
            "id": "rec-no-employees",
            "type": "onboarding",
            "priority": "medium",
            "title": "AI 团队尚未配置",
            "problem": "系统中还没有 AI 员工。",
            "impact": "没有 AI 员工则无法自动执行任务与工作流。",
            "analysis": "完成上手向导后即可创建 AI 员工并分配目标。",
            "suggestion": "前往上手向导创建第一个 AI 员工。",
            "action_label": "开始上手",
            "action_url": "/onboarding",
            "created_at": now.isoformat(),
        })

    # 按优先级排序（high > medium > low）
    _priority_rank = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda x: _priority_rank.get(x.get("priority", "low"), 3))
    recommendations = recommendations[:6]

    # 5. 最近模型调用（真实成本记录）
    model_rows = (
        await db.execute(
            select(
                AiCostRecordModel.provider,
                AiCostRecordModel.model,
                AiCostRecordModel.total_tokens,
                AiCostRecordModel.status,
                AiCostRecordModel.created_at,
            )
            .order_by(AiCostRecordModel.created_at.desc())
            .limit(limit)
        )
    ).all()
    model_calls = [
        {
            "provider": r.provider,
            "model": r.model,
            "total_tokens": r.total_tokens,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in model_rows
    ]

    # 6. 知识 / 记忆活动
    doc_count = (
        await db.execute(select(func.count(DocumentModel.id)))
    ).scalar() or 0
    mem_rows = (
        await db.execute(
            select(
                AgentMemoryModel.agent_id,
                AgentMemoryModel.role,
                AgentMemoryModel.content,
                AgentMemoryModel.created_at,
            )
            .order_by(AgentMemoryModel.created_at.desc())
            .limit(6)
        )
    ).all()
    memory_activity = [
        {
            "agent_name": emp_name_by_id.get(str(r.agent_id), "AI"),
            "role": r.role,
            "excerpt": (r.content or "")[:80],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in mem_rows
    ]

    # 7. 最近审计事件
    audit_rows = (
        await db.execute(
            select(
                AuditLog.id,
                AuditLog.action,
                AuditLog.resource_type,
                AuditLog.status,
                AuditLog.timestamp,
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
    ).all()
    audit_activity = [
        {
            "action": r.action,
            "resource_type": r.resource_type,
            "status": r.status,
            "created_at": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in audit_rows
    ]

    return {
        "server_time": datetime.now(UTC).isoformat(),
        "employees": employees,
        "active_employees": active_employees,
        "total_employees": len(employees),
        "running_tasks": running_task_count,
        "blocked_tasks": int(blocked_count or 0),
        "failed_tasks": int(failed_count or 0),
        "today": {
            "completed": completed_today,
            "failed": failed_today,
        },
        "working_now": working_now,
        "recommendations": recommendations,
        "recent_tasks": recent_tasks,
        "workflows": workflows,
        "goals": goals[:6],
        "model_calls": model_calls,
        "knowledge": {"documents": doc_count, "memory_activity": memory_activity},
        "audit_activity": audit_activity,
    }


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    获取 CEO 仪表板核心统计数据
    """
    logger.info("fetching_dashboard_stats", user_id=current_user.id)
    
    # 供应商总数
    total_suppliers_result = await db.execute(
        select(func.count(Supplier.id))
    )
    total_suppliers = total_suppliers_result.scalar() or 0
    
    # 活跃供应商数
    active_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.status == SupplierStatus.ACTIVE
        )
    )
    active_suppliers = active_suppliers_result.scalar() or 0
    
    # 本月新增供应商
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    new_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.created_at >= thirty_days_ago
        )
    )
    new_suppliers = new_suppliers_result.scalar() or 0
    
    # 高风险供应商数（risk_score 为综合评分 0-100，分数越低风险越高；<60 即 HIGH/CRITICAL）
    high_risk_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.risk_score.isnot(None),
            Supplier.risk_score < 60,
        )
    )
    high_risk_suppliers = high_risk_result.scalar() or 0

    # 按业务类型统计
    business_type_stats = []
    for biz_type in BusinessType:
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.business_type == biz_type
            )
        )
        count = count_result.scalar() or 0
        business_type_stats.append({
            "type": biz_type.value,
            "count": count
        })

    # 按风险等级统计（阈值与 SupplierCRUD 保持一致：>=80 low, >=60 medium, >=40 high, <40 critical）
    risk_buckets = {
        "low": Supplier.risk_score >= 80,
        "medium": (Supplier.risk_score >= 60) & (Supplier.risk_score < 80),
        "high": (Supplier.risk_score >= 40) & (Supplier.risk_score < 60),
        "critical": Supplier.risk_score < 40,
    }
    risk_distribution = {}
    for risk_level, condition in risk_buckets.items():
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.risk_score.isnot(None),
                condition,
            )
        )
        count = count_result.scalar() or 0
        risk_distribution[risk_level] = count
    
    return {
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "new_suppliers_this_month": new_suppliers,
        "high_risk_suppliers": high_risk_suppliers,
        "business_type_distribution": business_type_stats,
        "risk_distribution": risk_distribution,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    Get CEO dashboard overview with key metrics.
    """
    logger.info("fetching_dashboard_overview", user_id=current_user.id)

    # AI employees count
    emp_result = await db.execute(select(func.count(AIEmployeeModel.id)))
    ai_employees = emp_result.scalar() or 0

    # Task stats
    running_result = await db.execute(
        select(func.count(TaskModel.id)).where(TaskModel.status == "running")
    )
    running_tasks = running_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(TaskModel.id)).where(TaskModel.status == "completed")
    )
    completed_tasks = completed_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(TaskModel.id)).where(TaskModel.status == "failed")
    )
    failed_tasks = failed_result.scalar() or 0

    # System components
    components = [
        {"name": "AI Brain", "status": "online", "load": 85},
        {"name": "Database", "status": "online", "load": 62},
        {"name": "API Gateway", "status": "online", "load": 45},
        {"name": "Security", "status": "protected", "load": 100},
    ]

    return {
        "ai_employees": ai_employees,
        "running_tasks": running_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "system_health": "online",
        "components": components,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@router.get("/trends")
async def get_dashboard_trends(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    获取趋势数据（过去 N 天）
    """
    logger.info("fetching_dashboard_trends", user_id=current_user.id, days=days)
    
    # 计算日期范围
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)
    
    # 每日新增供应商趋势
    daily_new_suppliers = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.created_at >= day_start,
                Supplier.created_at < day_end
            )
        )
        count = count_result.scalar() or 0
        daily_new_suppliers.append({
            "date": day_start.date().isoformat(),
            "count": count
        })
    
    return {
        "period": {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "days": days
        },
        "daily_new_suppliers": daily_new_suppliers,
    }


@router.get("/top-suppliers")
async def get_top_suppliers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取优质供应商列表（低风险 + 活跃）
    """
    logger.info("fetching_top_suppliers", user_id=current_user.id, limit=limit)
    
    result = await db.execute(
        select(Supplier)
        .where(
            Supplier.status == SupplierStatus.ACTIVE,
            Supplier.risk_level == "low"
        )
        .order_by(Supplier.created_at.desc())
        .limit(limit)
    )
    suppliers = result.scalars().all()
    
    return [
        {
            "id": str(supplier.id),
            "name": supplier.name,
            "business_type": supplier.business_type.value,
            "risk_level": supplier.risk_level,
            "status": supplier.status.value,
            "contact_email": supplier.contact_email,
        }
        for supplier in suppliers
    ]


@router.get("/alerts")
async def get_dashboard_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取需要关注的警报
    """
    logger.info("fetching_dashboard_alerts", user_id=current_user.id)
    
    alerts = []
    
    # 高风险供应商警报（risk_score 为综合评分 0-100，分数越低风险越高；<60 为 HIGH/CRITICAL）
    high_risk_result = await db.execute(
        select(Supplier).where(
            Supplier.risk_score.isnot(None),
            Supplier.risk_score < 60,
            Supplier.status == SupplierStatus.ACTIVE
        )
    )
    high_risk_suppliers = high_risk_result.scalars().all()
    
    for supplier in high_risk_suppliers:
        is_critical = (supplier.risk_score or 0) < 40
        alerts.append({
            "type": "high_risk",
            "severity": "critical" if is_critical else "high",
            "title": f"高风险供应商: {supplier.name}",
            "message": f"供应商 {supplier.name} 综合风险评分为 {supplier.risk_score:.0f}（低于 60），建议审查",
            "supplier_id": str(supplier.id),
            "created_at": datetime.now(UTC).isoformat(),
        })
    
    # 黑名单供应商警报
    blacklist_result = await db.execute(
        select(Supplier).where(
            Supplier.status == SupplierStatus.BLACKLIST
        )
    )
    blacklist_suppliers = blacklist_result.scalars().all()
    
    for supplier in blacklist_suppliers:
        alerts.append({
            "type": "blacklist",
            "severity": "critical",
            "title": f"黑名单供应商: {supplier.name}",
            "message": f"供应商 {supplier.name} 已被列入黑名单",
            "supplier_id": str(supplier.id),
            "created_at": datetime.now(UTC).isoformat(),
        })
    
    return alerts


@router.get("/system-health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    系统健康状态（Y1.0：全部为真实探测/真实落库数据，无硬编码负载）。

    - Database: SELECT 1 连通性探测；PostgreSQL 额外返回连接数占 max_connections 比例
    - AI Brain: 近 1 小时 ai_cost_records 真实调用统计（成功率/平均延迟/调用数）
    - API Gateway: 本请求成功服务即 online
    - Security: RBAC/Auth 中间件在线即 protected
    """
    from sqlalchemy import text

    from src.database.models import AiCostRecordModel

    logger.info("fetching_system_health", user_id=current_user.id)

    now = datetime.now(UTC)

    # --- Database: real connectivity + connection load (PG only) ---
    db_status = "online"
    db_load = None
    db_detail = ""
    try:
        await db.execute(text("SELECT 1"))
        if db.bind.dialect.name == "postgresql":
            row = (
                await db.execute(
                    text(
                        "SELECT (SELECT count(*) FROM pg_stat_activity)::int, "
                        "(SELECT setting::int FROM pg_settings "
                        " WHERE name = 'max_connections')"
                    )
                )
            ).first()
            active_conns, max_conns = int(row[0]), int(row[1])
            db_load = round(active_conns / max_conns * 100) if max_conns else None
            db_detail = f"{active_conns}/{max_conns} connections"
    except Exception as e:
        db_status = "degraded"
        db_detail = f"db check failed: {str(e)[:120]}"
        logger.warning("system_health_db_check_failed", error=str(e))

    # --- AI Brain: real provider stats from persisted cost records (1h window) ---
    since = now - timedelta(hours=1)
    cost_rows = (
        await db.execute(
            select(AiCostRecordModel.latency_ms, AiCostRecordModel.status).where(
                AiCostRecordModel.created_at >= since
            )
        )
    ).all()
    total_calls = len(cost_rows)
    success_calls = sum(1 for r in cost_rows if r[1] == "success")
    latencies = [r[0] for r in cost_rows if r[0] is not None]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else None
    success_rate = round(success_calls / total_calls * 100) if total_calls else None
    # No calls in the window means the brain is idle, not unhealthy; only
    # mark degraded when every recent call failed.
    ai_status = "degraded" if total_calls > 0 and success_calls == 0 else "online"

    overall = "healthy" if db_status == "online" and ai_status == "online" else "degraded"

    return {
        "overall_status": overall,
        "components": [
            {
                "name": "AI Brain",
                "status": ai_status,
                "load": None,
                "latency_ms": avg_latency,
                "success_rate": success_rate,
                "calls_last_hour": total_calls,
                "last_check": now.isoformat(),
            },
            {
                "name": "Database",
                "status": db_status,
                "load": db_load,
                "detail": db_detail,
                "last_check": now.isoformat(),
            },
            {
                "name": "API Gateway",
                "status": "online",
                "load": None,
                "last_check": now.isoformat(),
            },
            {
                "name": "Security",
                "status": "protected",
                "load": None,
                "last_check": now.isoformat(),
            },
        ],
        "ai_calls_last_hour": total_calls,
        "last_updated": now.isoformat(),
    }


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取最近活动记录
    """
    logger.info("fetching_recent_activity", user_id=current_user.id, limit=limit)
    
    # 查询最近创建的供应商
    result = await db.execute(
        select(Supplier)
        .order_by(Supplier.created_at.desc())
        .limit(limit)
    )
    suppliers = result.scalars().all()
    
    activities = []
    for supplier in suppliers:
        time_diff = datetime.now(UTC) - supplier.created_at
        if time_diff.seconds < 3600:
            time_ago = f"{time_diff.seconds // 60}分钟前"
        elif time_diff.days == 0:
            time_ago = f"{time_diff.seconds // 3600}小时前"
        else:
            time_ago = f"{time_diff.days}天前"
        
        activities.append({
            "type": "supplier_created",
            "icon": "package",
            "event": f"新增供应商: {supplier.name}",
            "time": time_ago,
            "timestamp": supplier.created_at.isoformat(),
            "metadata": {
                "supplier_id": str(supplier.id),
                "business_type": supplier.business_type.value,
            }
        })
    
    return activities



@router.get("/activities")
async def get_dashboard_activities(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """P0-2 真实 Dashboard 活动流：聚合 audit / tasks / workflow executions，按时间倒序。

    无数据时返回 []；绝不返回硬编码 demo 条目。
    """
    from src.identity.models import AuditLog
    from src.database.models import TaskModel, WorkflowExecutionModel

    logger.info("fetching_dashboard_activities", user_id=current_user.id, limit=limit)
    limit = max(1, min(limit, 100))
    items: list[dict] = []

    # --- Audit logs (auth, rbac, user management, policy actions) ---
    # 不加载 user relationship（避免某些 SQLite 场景的 lazy-loading 报错）
    from sqlalchemy.orm import selectinload
    audit_rows = (await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )).scalars().all()
    for a in audit_rows:
        actor = current_user.full_name or current_user.username
        try:
            usr = a.user
            if usr is not None:
                actor = getattr(usr, "full_name", None) or getattr(usr, "username", None) or actor
        except Exception:
            pass
        ts = a.timestamp
        if ts:
            iso = ts.isoformat()
            if ts.tzinfo is None:
                iso += "Z"
        else:
            iso = datetime.now(UTC).isoformat()
        items.append({
            "id": f"audit-{a.id}",
            "timestamp": iso,
            "category": "audit",
            "actor": actor,
            "action_summary": f"{a.action} {a.resource_type}" + (f" (id={a.resource_id})" if a.resource_id else ""),
            "status": a.status or "success",
            "detail_url": None,
        })

    # --- Tasks ---
    task_rows = (await db.execute(
        select(TaskModel)
        .order_by(getattr(TaskModel, "created_at").desc())
        .limit(limit)
    )).scalars().all()
    for t in task_rows:
        ts = getattr(t, "created_at", None) or getattr(t, "updated_at", None)
        ts_iso = ts.isoformat() if ts is not None else datetime.now(UTC).isoformat()
        if ts and ts.tzinfo is None:
            ts_iso = ts_iso + "Z"
        items.append({
            "id": f"task-{t.id}",
            "timestamp": ts_iso,
            "category": "task",
            "actor": "系统调度" if not getattr(t, "creator_id", None) else f"用户#{t.creator_id}",
            "action_summary": t.title or f"任务 {t.id}",
            "status": (t.status or "pending"),
            "detail_url": f"/workflow?task={t.id}" if getattr(t, "id", None) else None,
        })

    # --- Workflow executions ---
    wfe_rows = (await db.execute(
        select(WorkflowExecutionModel)
        .order_by(WorkflowExecutionModel.created_at.desc())
        .limit(limit)
    )).scalars().all()
    for w in wfe_rows:
        ts = getattr(w, "started_at", None) or getattr(w, "created_at", None)
        ts_iso = ts.isoformat() if ts is not None else datetime.now(UTC).isoformat()
        if ts and ts.tzinfo is None:
            ts_iso = ts_iso + "Z"
        items.append({
            "id": f"wf-{w.id}",
            "timestamp": ts_iso,
            "category": "workflow",
            "actor": f"用户#{getattr(w, 'user_id', '')}" if getattr(w, "user_id", None) else "系统调度",
            "action_summary": f"执行工作流 #{getattr(w, 'workflow_id', '')}",
            "status": (w.status or "pending"),
            "detail_url": f"/workflow?execution={w.id}" if getattr(w, "id", None) else None,
        })

    # Sort by timestamp desc
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:limit]

