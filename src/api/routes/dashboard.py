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
    )
    from src.database.models import AiCostRecordModel
    from src.identity.models import AuditLog

    limit = max(1, min(limit, 30))

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

    # 2. 最近任务（含成败摘要）
    task_rows = (
        await db.execute(
            select(
                TaskModel.id,
                TaskModel.title,
                TaskModel.status,
                TaskModel.updated_at,
                TaskModel.result_data,
                TaskModel.error,
                TaskModel.assigned_to,
            )
            .order_by(TaskModel.updated_at.desc())
            .limit(limit)
        )
    ).all()
    task_map = {str(r.id): r for r in task_rows}

    def _task_summary(result_data) -> str:
        if not result_data:
            return ""
        if isinstance(result_data, dict):
            out = result_data.get("output") or ""
            name = result_data.get("employee_name") or ""
            if out:
                return f"{name}: {str(out)[:80]}" if name else str(out)[:80]
        return str(result_data)[:80]

    emp_name_by_id = {e["id"]: e["name"] for e in employees}
    recent_tasks = [
        {
            "id": str(r.id),
            "title": r.title,
            "status": r.status,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "summary": _task_summary(r.result_data),
            "error": (r.error or "")[:120] if r.error else None,
            "employee_name": emp_name_by_id.get(str(r.assigned_to)) if r.assigned_to else None,
        }
        for r in task_rows
    ]

    running_tasks = (
        await db.execute(select(func.count(TaskModel.id)).where(TaskModel.status == "running"))
    ).scalar() or 0

    # 3. 最近工作流执行
    wf_rows = (
        await db.execute(
            select(
                WorkflowExecutionModel.id,
                WorkflowExecutionModel.status,
                WorkflowExecutionModel.started_at,
                WorkflowExecutionModel.error,
            )
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(5)
        )
    ).all()
    workflows = [
        {
            "execution_id": str(r.id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "error": (r.error or "")[:120] if r.error else None,
        }
        for r in wf_rows
    ]

    # 4. 目标进度
    goal_rows = (
        await db.execute(
            select(
                GoalModel.id,
                GoalModel.title,
                GoalModel.status,
                GoalModel.progress_pct,
                GoalModel.kpi_name,
                GoalModel.kpi_current,
                GoalModel.kpi_target,
                GoalModel.budget_total,
                GoalModel.budget_spent,
                GoalModel.updated_at,
            )
            .order_by(GoalModel.updated_at.desc())
            .limit(5)
        )
    ).all()
    goals = [
        {
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "progress_pct": r.progress_pct,
            "kpi_name": r.kpi_name,
            "kpi_current": r.kpi_current,
            "kpi_target": r.kpi_target,
            "budget_total": r.budget_total,
            "budget_spent": r.budget_spent,
        }
        for r in goal_rows
    ]

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
        "running_tasks": running_tasks,
        "recent_tasks": recent_tasks,
        "workflows": workflows,
        "goals": goals,
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

