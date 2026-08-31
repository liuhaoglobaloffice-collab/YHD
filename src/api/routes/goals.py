"""
Goal API Routes — 老板目标中心

提供目标 CRUD、激活、进度跟踪、失败恢复管理。
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.ai.goal_service import GoalService
from src.ai.recovery import RecoveryChain
from src.ai.recovery_executor import RecoveryExecutor
from src.database.models import FailureRecordModel
from src.identity.models import AccountType, User

router = APIRouter(prefix="/goals", tags=["Goals"])


def get_goal_service(session: AsyncSession = Depends(get_db)) -> GoalService:
    return GoalService(session)


def get_recovery_chain(session: AsyncSession = Depends(get_db)) -> RecoveryChain:
    return RecoveryChain(session)


# ==================== 全局失败记录（必须在 {goal_id} 前注册） ====================


@router.get("/failures", tags=["Failures"])
async def list_all_failures(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取全局失败记录列表。"""
    recovery = RecoveryChain(session)
    return await recovery.get_failure_records(category=category, page=page, page_size=page_size)


@router.post("/failures/{record_id}/strategy")
async def determine_failure_strategy(
    record_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """确定失败恢复策略。"""
    recovery = RecoveryChain(session)
    record = await session.get(FailureRecordModel, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="失败记录不存在")
    strategy = await recovery.determine_strategy(record)
    return {"record_id": record_id, "strategy": strategy.value, "detail": record.strategy_detail}


@router.post("/failures/{record_id}/lesson")
async def record_lesson(
    record_id: int,
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """记录失败经验教训。"""
    recovery = RecoveryChain(session)
    try:
        record = await recovery.record_lesson(
            record_id=record_id,
            lesson=body.get("lesson", ""),
            is_successful=body.get("is_successful", False),
        )
        return recovery._to_dict(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/failures/{record_id}/boss-decision")
async def boss_decision(
    record_id: int,
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """老板对失败恢复做出决策。"""
    recovery = RecoveryChain(session)
    try:
        record = await recovery.notify_boss(
            record_id=record_id,
            boss_decision=body.get("decision"),
        )
        return recovery._to_dict(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/failures/{record_id}/execute-strategy")
async def execute_recovery_strategy(
    record_id: int,
    body: Optional[Dict[str, Any]] = {},
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """手动执行失败恢复策略。"""
    executor = RecoveryExecutor(session)
    record = await session.get(FailureRecordModel, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="失败记录不存在")
    try:
        result = await executor.execute_strategy(record, context=body.get("context", {}))
        return {
            "record_id": record_id,
            "success": result.success,
            "action": result.action,
            "message": result.message,
            "retry_count": result.retry_count,
            "details": result.details,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"策略执行失败: {str(e)}")


# ==================== 目标管理 ====================


@router.post("", status_code=201)
async def create_goal(
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """创建新目标。"""
    service = GoalService(session)
    try:
        goal = await service.create_goal(
            title=body.get("title", ""),
            description=body.get("description"),
            priority=body.get("priority", "normal"),
            kpi_name=body.get("kpi_name"),
            kpi_target=body.get("kpi_target"),
            kpi_unit=body.get("kpi_unit"),
            budget_total=body.get("budget_total"),
            time_start=(
                datetime.fromisoformat(body["time_start"]) if body.get("time_start") else None
            ),
            time_end=(
                datetime.fromisoformat(body["time_end"]) if body.get("time_end") else None
            ),
            user=current_user,
        )
        return service._to_dict(goal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/from-text", status_code=201)
async def create_goal_from_text(
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """P0-1 LLM 目标理解：老板一句自然语言 → 自动提取 KPI/预算/时间/风险并创建目标。

    请求体: {"text": "帮我开发美国市场，30天获取100个潜在客户，预算2000美元"}
    无可用 LLM Provider 时诚实降级为规则解析（parse_method=rule_based）。
    """
    service = GoalService(session)
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    try:
        goal, parse_info = await service.create_goal_from_text(
            text=text,
            user=current_user,
        )
        result = service._to_dict(goal)
        result["parse_info"] = parse_info
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"目标创建失败: {str(e)}")


@router.get("")
async def list_goals(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取目标列表。"""
    # V4 可见性：主账号/管理员看全部目标（CEO 驾驶舱 drill-down 一致）；子账号/普通用户只看自己创建的
    is_owner = (
        current_user.account_type == AccountType.OWNER
        or getattr(current_user, "is_superuser", False)
        or str(getattr(current_user, "role", "")).upper() == "ADMIN"
    )
    service = GoalService(session)
    return await service.list_goals(
        status=status,
        priority=priority,
        created_by=None if is_owner else current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get("/{goal_id}")
async def get_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取单个目标详情。"""
    service = GoalService(session)
    goal = await service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    return service._to_dict(goal)


@router.post("/{goal_id}/activate")
async def activate_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """激活目标：自动解析→规划→路由→生成执行计划。"""
    service = GoalService(session)
    try:
        goal = await service.activate_goal(goal_id, current_user)
        return service._to_dict(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{goal_id}/execute")
async def execute_goal_workflow(
    goal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """执行目标关联的工作流：执行→更新目标状态。"""
    service = GoalService(session)
    try:
        goal = await service.execute_goal_workflow(goal_id, current_user)
        return service._to_dict(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{goal_id}/progress")
async def update_goal_progress(
    goal_id: int,
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """更新目标进度。"""
    service = GoalService(session)
    try:
        goal = await service.update_progress(
            goal_id,
            progress_pct=body.get("progress_pct", 0),
            kpi_current=body.get("kpi_current"),
        )
        return service._to_dict(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{goal_id}/complete")
async def complete_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """完成目标。"""
    service = GoalService(session)
    try:
        goal = await service.complete_goal(goal_id)
        return service._to_dict(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{goal_id}/cancel")
async def cancel_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """取消目标。"""
    service = GoalService(session)
    try:
        goal = await service.cancel_goal(goal_id)
        return service._to_dict(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 目标关联的失败恢复 ====================


@router.post("/{goal_id}/failures")
async def record_failure(
    goal_id: int,
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """记录目标关联的失败事件。"""
    recovery = RecoveryChain(session)
    try:
        record = await recovery.record_failure(
            failure_summary=body.get("summary", ""),
            failure_detail=body.get("detail"),
            goal_id=goal_id,
            task_id=body.get("task_id"),
            workflow_id=body.get("workflow_id"),
            created_by=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
        )
        return recovery._to_dict(record)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{goal_id}/failures")
async def list_goal_failures(
    goal_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取目标关联的失败记录。"""
    recovery = RecoveryChain(session)
    return await recovery.get_failure_records(goal_id=goal_id, page=page, page_size=page_size)