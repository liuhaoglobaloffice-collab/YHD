"""Business Scheduler — P0 自主经营调度服务。

设计原则（与项目既有约束一致）：
- 复用既有执行链：Goal 激活/执行走 GoalService（Planner → AgentRouter →
  WorkflowBridge → WorkflowExecutor → TaskExecutor），不复制任何业务逻辑
- 诚实执行：每个 Goal 的执行结果（completed/failed）由 GoalService 真实落盘，
  调度器只记录统计，不伪造成功
- 失败安全：单个 Goal 执行失败不影响同周期其他 Goal；异常只记日志
- 零新增依赖：asyncio 后台循环 + 既有 SQLAlchemy 会话工厂
- 预算安全：预算拦截由既有 CostTracker 在任务执行层强制，调度器不绕过
"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# 单周期最少间隔（秒），防止误配置导致的高频空转
MIN_INTERVAL_SECONDS = 30


class BusinessScheduler:
    """自主经营调度器：周期性执行 Goal / 记忆清理等经营任务。"""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        settings: Optional[Any] = None,
    ):
        self._session_factory = session_factory
        self._settings = settings or get_settings()
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._runs = 0
        self._last_run_at: Optional[datetime] = None
        self._last_error: Optional[str] = None

    # ========== 生命周期 ==========

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """启动后台调度循环（幂等）。"""
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "scheduler_started",
            interval_seconds=self.interval_seconds,
            auto_activate=self._settings.scheduler_auto_activate,
        )

    async def stop(self, timeout: float = 10.0) -> None:
        """停止调度循环（等待当前周期结束，超时强制取消）。"""
        self._stop_event.set()
        if self._task is None:
            return
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
        except asyncio.TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
        logger.info("scheduler_stopped", runs=self._runs)

    @property
    def interval_seconds(self) -> int:
        return max(MIN_INTERVAL_SECONDS, int(self._settings.scheduler_interval_seconds))

    def status(self) -> Dict[str, Any]:
        """调度器运行状态（供 /health/ready 与运维查看）。"""
        return {
            "enabled": bool(self._settings.scheduler_enabled),
            "running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "auto_activate": bool(self._settings.scheduler_auto_activate),
            "runs": self._runs,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_error": self._last_error,
        }

    # ========== 主循环 ==========

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as e:  # noqa: BLE001
                self._last_error = str(e)
                logger.error("scheduler_cycle_failed", error=str(e))
            # 等待间隔或停止信号（可被 stop() 立即唤醒）
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    async def run_once(self) -> Dict[str, Any]:
        """执行一个调度周期（测试可直接调用，不依赖后台循环）。

        Returns:
            {"goals_activated": n, "goals_executed": n, "memories_cleaned": n}
        """
        self._runs += 1
        self._last_run_at = datetime.now(UTC)

        activated = 0
        executed = 0
        cleaned = 0

        async with self._session_factory() as session:
            if self._settings.scheduler_auto_activate:
                activated = await self._auto_activate_drafts(session)
            executed = await self._auto_execute_goals(session)
            cleaned = await self._cleanup_expired_memories(session)

        result = {
            "goals_activated": activated,
            "goals_executed": executed,
            "memories_cleaned": cleaned,
        }
        logger.info("scheduler_cycle_completed", **result)
        return result

    # ========== 调度任务 ==========

    async def _auto_activate_drafts(self, session) -> int:
        """自动激活 draft 目标（SCHEDULER_AUTO_ACTIVATE 开启时）。

        复用 GoalService.activate_goal：解析 → 规划 → 员工路由 → Workflow 生成。
        无可用 AI 员工时 activate_goal 会真实报错，此处记录并跳过。
        """
        from src.ai.goal_service import GoalService
        from src.database.models import GoalModel

        limit = int(self._settings.scheduler_max_goals_per_cycle)
        result = await session.execute(
            select(GoalModel)
            .where(GoalModel.status == "draft")
            .order_by(GoalModel.created_at.asc())
            .limit(limit)
        )
        goals = list(result.scalars().all())
        count = 0
        service = GoalService(session)
        for goal in goals:
            user = await self._load_creator(session, goal)
            if user is None:
                continue
            try:
                await service.activate_goal(goal.id, user)
                count += 1
                logger.info("scheduler_goal_activated", goal_id=goal.id)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "scheduler_goal_activation_failed",
                    goal_id=goal.id,
                    error=str(e),
                )
        return count

    async def _auto_execute_goals(self, session) -> int:
        """自动执行 active 状态的 Goal（老板不在线的核心自主执行环）。

        复用 GoalService.execute_goal_workflow：
        Workflow → Task → AI 员工真实执行 → 结果/Cost/Recovery 全链路落盘。
        执行完成后 Goal 状态流转为 completed/failed（终态不再重复执行）。
        """
        from src.ai.goal_service import GoalService
        from src.database.models import GoalModel

        limit = int(self._settings.scheduler_max_goals_per_cycle)
        result = await session.execute(
            select(GoalModel)
            .where(GoalModel.status == "active")
            .order_by(GoalModel.created_at.asc())
            .limit(limit)
        )
        goals = list(result.scalars().all())
        if not goals:
            return 0

        count = 0
        service = GoalService(session)
        for goal in goals:
            user = await self._load_creator(session, goal)
            if user is None:
                continue
            try:
                updated = await service.execute_goal_workflow(goal.id, user)
                logger.info(
                    "scheduler_goal_executed",
                    goal_id=goal.id,
                    goal_status=updated.status,
                )
                count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "scheduler_goal_execution_failed",
                    goal_id=goal.id,
                    error=str(e),
                )
        return count

    async def _cleanup_expired_memories(self, session) -> int:
        """清理过期短期记忆（复用 AgentMemoryStore 分级策略，核心记忆永久保留）。"""
        try:
            from src.ai.memory_store import AgentMemoryStore

            deleted, _total = await AgentMemoryStore(session).cleanup_expired()
            return deleted
        except Exception as e:  # noqa: BLE001
            logger.warning("scheduler_memory_cleanup_failed", error=str(e))
            return 0

    async def _load_creator(self, session, goal):
        """加载目标创建者（执行链 RBAC 需要真实 User；加载失败跳过该目标）。"""
        from src.identity.models import User

        if not goal.created_by:
            logger.warning("scheduler_goal_has_no_creator", goal_id=goal.id)
            return None
        user = await session.get(User, goal.created_by)
        if user is None:
            logger.warning(
                "scheduler_goal_creator_missing", goal_id=goal.id, created_by=goal.created_by
            )
        return user


# ==================== 进程级单例（跟随 FastAPI lifespan） ====================

_scheduler: Optional[BusinessScheduler] = None


def get_business_scheduler() -> Optional[BusinessScheduler]:
    """获取当前调度器实例（未启动时为 None，供 health 状态展示）。"""
    return _scheduler


async def start_business_scheduler() -> Optional[BusinessScheduler]:
    """按配置启动调度器（settings.scheduler_enabled=False 时不启动）。"""
    global _scheduler
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled_by_config")
        return None

    from src.api.dependencies.database import get_session_factory

    _scheduler = BusinessScheduler(get_session_factory(), settings)
    _scheduler.start()
    return _scheduler


async def stop_business_scheduler() -> None:
    """停止调度器（应用关闭时调用）。"""
    global _scheduler
    if _scheduler is not None:
        await _scheduler.stop()
        _scheduler = None
