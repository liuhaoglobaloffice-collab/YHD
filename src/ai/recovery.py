"""
Failure Recovery Chain — 失败恢复链

实现:
1. 失败原因分类和分析
2. 策略调整（更换 AI 员工/Provider/参数）
3. 失败经验沉淀
4. 安全阈值→请求老板
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import FailureRecordModel

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """失败原因分类。"""
    PROVIDER_ERROR = "provider_error"          # AI Provider 不可用/返回错误
    NETWORK_ERROR = "network_error"            # 网络连接失败
    TIMEOUT = "timeout"                        # 执行超时
    RATE_LIMIT = "rate_limit"                  # 速率限制
    AUTH_ERROR = "auth_error"                  # 认证失败
    AGENT_ERROR = "agent_error"                # Agent 执行错误
    BUSINESS_LOGIC_ERROR = "business_logic_error"  # 业务逻辑错误
    INVALID_INPUT = "invalid_input"            # 无效输入
    BUDGET_EXCEEDED = "budget_exceeded"        # 超预算
    UNKNOWN = "unknown"                        # 未知错误


class StrategyAction(str, Enum):
    """策略调整动作。"""
    RETRY = "retry"                            # 直接重试
    SWITCH_AGENT = "switch_agent"              # 更换 AI 员工
    SWITCH_PROVIDER = "switch_provider"        # 更换 Provider
    ADJUST_PARAMS = "adjust_params"            # 调整参数
    CHANGE_APPROACH = "change_approach"        # 更换执行方案
    REQUEST_BOSS = "request_boss"              # 请求老板决策
    ABORT = "abort"                            # 终止


class RecoveryChain:
    """失败恢复链 — 分析失败原因 → 调整策略 → 经验沉淀。"""

    # 安全阈值配置
    SAFETY_THRESHOLDS = {
        "max_retries": 3,                       # 最大重试次数
        "max_cost_per_task": 50.0,              # 单任务最大成本（USD）
        "max_consecutive_failures": 3,          # 最大连续失败次数
        "max_duration_minutes": 120,            # 单任务最大执行时间（分钟）
    }

    # 失败分类 → 默认策略映射
    CATEGORY_STRATEGY = {
        FailureCategory.PROVIDER_ERROR: [StrategyAction.RETRY, StrategyAction.SWITCH_PROVIDER, StrategyAction.REQUEST_BOSS],
        FailureCategory.NETWORK_ERROR: [StrategyAction.RETRY, StrategyAction.ADJUST_PARAMS, StrategyAction.ABORT],
        FailureCategory.TIMEOUT: [StrategyAction.RETRY, StrategyAction.ADJUST_PARAMS, StrategyAction.SWITCH_AGENT],
        FailureCategory.RATE_LIMIT: [StrategyAction.RETRY, StrategyAction.ADJUST_PARAMS, StrategyAction.REQUEST_BOSS],
        FailureCategory.AUTH_ERROR: [StrategyAction.REQUEST_BOSS, StrategyAction.ABORT],
        FailureCategory.AGENT_ERROR: [StrategyAction.RETRY, StrategyAction.SWITCH_AGENT, StrategyAction.CHANGE_APPROACH],
        FailureCategory.BUSINESS_LOGIC_ERROR: [StrategyAction.CHANGE_APPROACH, StrategyAction.REQUEST_BOSS],
        FailureCategory.INVALID_INPUT: [StrategyAction.ADJUST_PARAMS, StrategyAction.REQUEST_BOSS],
        FailureCategory.BUDGET_EXCEEDED: [StrategyAction.REQUEST_BOSS, StrategyAction.ABORT],
        FailureCategory.UNKNOWN: [StrategyAction.RETRY, StrategyAction.REQUEST_BOSS],
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_failure(
        self,
        failure_summary: str,
        failure_detail: Optional[str] = None,
        goal_id: Optional[int] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        created_by: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> FailureRecordModel:
        """记录失败事件并自动分类。"""
        category = self._classify_failure(failure_summary, failure_detail)

        record = FailureRecordModel(
            goal_id=goal_id,
            task_id=task_id,
            workflow_id=workflow_id,
            failure_category=category.value,
            failure_summary=failure_summary,
            failure_detail=failure_detail,
            retry_count=0,
            max_retries=self.SAFETY_THRESHOLDS["max_retries"],
            created_by=created_by or 0,
            tenant_id=tenant_id,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        logger.info(f"Recorded failure: id={record.id}, category={category.value}, summary='{failure_summary[:50]}'")
        return record

    def _classify_failure(self, summary: str, detail: Optional[str] = None) -> FailureCategory:
        """基于内容和关键词自动分类失败原因。"""
        text = f"{summary} {detail or ''}".lower()

        # Provider 错误
        if any(kw in text for kw in ["provider", "api error", "openai", "ollama", "llm", "model", "500", "502", "503"]):
            return FailureCategory.PROVIDER_ERROR

        # 网络错误
        if any(kw in text for kw in ["network", "connection", "timeout", "connect", "dns", "refused"]):
            if "timeout" in text:
                return FailureCategory.TIMEOUT
            return FailureCategory.NETWORK_ERROR

        # 速率限制
        if any(kw in text for kw in ["rate limit", "429", "too many requests", "throttle"]):
            return FailureCategory.RATE_LIMIT

        # 认证错误
        if any(kw in text for kw in ["auth", "unauthorized", "403", "401", "token", "api key", "permission denied"]):
            return FailureCategory.AUTH_ERROR

        # Agent 错误
        if any(kw in text for kw in ["agent", "execution", "runtime", "attributeerror", "typeerror", "valueerror"]):
            return FailureCategory.AGENT_ERROR

        # 预算超限
        if any(kw in text for kw in ["budget", "cost limit", "over budget", "insufficient funds"]):
            return FailureCategory.BUDGET_EXCEEDED

        # 业务逻辑错误
        if any(kw in text for kw in ["business", "logic", "invalid", "validation", "constraint"]):
            return FailureCategory.BUSINESS_LOGIC_ERROR

        # 输入错误
        if any(kw in text for kw in ["input", "parameter", "argument", "missing"]):
            return FailureCategory.INVALID_INPUT

        return FailureCategory.UNKNOWN

    async def determine_strategy(
        self, record: FailureRecordModel, context: Optional[Dict[str, Any]] = None
    ) -> StrategyAction:
        """根据失败记录和上下文确定下一步策略。"""
        category = FailureCategory(record.failure_category)
        strategies = self.CATEGORY_STRATEGY.get(category, [StrategyAction.RETRY, StrategyAction.REQUEST_BOSS])

        # 检查是否超过安全阈值
        threshold_exceeded, reason = await self._check_safety_thresholds(record, context)

        if threshold_exceeded:
            record.threshold_exceeded = True
            record.boss_notified = True
            # 超过安全阈值 → 请求老板
            strategy = StrategyAction.REQUEST_BOSS
            record.strategy_action = strategy.value
            record.strategy_detail = {
                "action": strategy.value,
                "reason": reason,
                "thresholds": self.SAFETY_THRESHOLDS,
            }
            await self.session.commit()
            logger.warning(f"Safety threshold exceeded: {reason}")
            return strategy

        # 选择第一个可行的策略
        strategy = strategies[0]
        record.strategy_action = strategy.value
        record.strategy_detail = {
            "action": strategy.value,
            "available_strategies": [s.value for s in strategies],
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
        }

        if strategy == StrategyAction.RETRY:
            record.retry_count += 1

        await self.session.commit()
        return strategy

    async def _check_safety_thresholds(
        self, record: FailureRecordModel, context: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """检查是否超过安全阈值。"""
        ctx = context or {}

        # 重试次数超限
        if record.retry_count >= self.SAFETY_THRESHOLDS["max_retries"]:
            return True, f"Retry count ({record.retry_count}) exceeded limit ({self.SAFETY_THRESHOLDS['max_retries']})"

        # 成本超限
        task_cost = ctx.get("task_cost", 0)
        if task_cost > self.SAFETY_THRESHOLDS["max_cost_per_task"]:
            return True, f"Task cost (${task_cost}) exceeded limit (${self.SAFETY_THRESHOLDS['max_cost_per_task']})"

        # 连续失败次数
        if record.failure_category == FailureCategory.BUDGET_EXCEEDED.value:
            return True, "Budget exceeded, cannot continue without owner decision"

        return False, ""

    async def record_lesson(
        self, record_id: int, lesson: str, is_successful: bool
    ) -> FailureRecordModel:
        """记录经验教训。"""
        record = await self.session.get(FailureRecordModel, record_id)
        if not record:
            raise ValueError("失败记录不存在")
        record.lesson_learned = lesson
        record.is_successful = is_successful
        record.resolved_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(record)
        logger.info(f"Recorded lesson for failure {record_id}: {lesson[:50]}...")
        return record

    async def notify_boss(
        self, record_id: int, boss_decision: Optional[str] = None
    ) -> FailureRecordModel:
        """记录老板决策。"""
        record = await self.session.get(FailureRecordModel, record_id)
        if not record:
            raise ValueError("失败记录不存在")
        record.boss_notified = True
        if boss_decision:
            record.boss_decision = boss_decision
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_failure_records(
        self,
        goal_id: Optional[int] = None,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取失败记录列表。"""
        from sqlalchemy import select, func, desc

        query = select(FailureRecordModel)
        if goal_id:
            query = query.where(FailureRecordModel.goal_id == goal_id)
        if category:
            query = query.where(FailureRecordModel.failure_category == category)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one() or 0

        query = query.order_by(desc(FailureRecordModel.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.execute(query)).scalars().all())

        return {
            "items": [self._to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _to_dict(self, record: FailureRecordModel) -> Dict[str, Any]:
        return {
            "id": record.id,
            "goal_id": record.goal_id,
            "task_id": record.task_id,
            "workflow_id": record.workflow_id,
            "failure_category": record.failure_category,
            "failure_summary": record.failure_summary,
            "failure_detail": record.failure_detail,
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
            "strategy_action": record.strategy_action,
            "strategy_detail": record.strategy_detail,
            "lesson_learned": record.lesson_learned,
            "is_successful": record.is_successful,
            "threshold_exceeded": record.threshold_exceeded,
            "boss_notified": record.boss_notified,
            "boss_decision": record.boss_decision,
            "created_by": record.created_by,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
        }