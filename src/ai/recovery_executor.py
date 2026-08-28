"""
Recovery Executor — 自动执行失败恢复策略

根据 RecoveryChain 确定的策略，自动执行对应的恢复操作：
1. RETRY — 直接重试
2. SWITCH_AGENT — 更换 AI 员工
3. SWITCH_PROVIDER — 更换 Provider
4. ADJUST_PARAMS — 调整参数后重试
5. CHANGE_APPROACH — 更换执行方案
6. REQUEST_BOSS — 请求老板决策
7. ABORT — 终止
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.recovery import FailureCategory, RecoveryChain, StrategyAction
from src.database.models import FailureRecordModel

logger = logging.getLogger(__name__)


class StrategyExecutionResult:
    """策略执行结果。"""

    def __init__(
        self,
        success: bool,
        action: str,
        message: str,
        retry_count: int = 0,
        new_record_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.action = action
        self.message = message
        self.retry_count = retry_count
        self.new_record_id = new_record_id
        self.details = details or {}


class RecoveryExecutor:
    """
    失败恢复策略执行器。

    根据 RecoveryChain 确定的策略，自动执行对应的恢复操作。
    支持重试、切换 Agent/Provider、调整参数、请求老板等策略。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.recovery = RecoveryChain(session)

    async def execute_strategy(
        self, record: FailureRecordModel, context: Optional[Dict[str, Any]] = None
    ) -> StrategyExecutionResult:
        """根据失败记录执行恢复策略。"""
        ctx = context or {}
        strategy = StrategyAction(record.strategy_action) if record.strategy_action else None

        if not strategy:
            # 策略未确定，先确定策略
            strategy = await self.recovery.determine_strategy(record, ctx)

        logger.info(
            "executing_recovery_strategy",
            record_id=record.id,
            strategy=strategy.value,
            category=record.failure_category,
        )

        strategy_map = {
            StrategyAction.RETRY: self._execute_retry,
            StrategyAction.SWITCH_AGENT: self._execute_switch_agent,
            StrategyAction.SWITCH_PROVIDER: self._execute_switch_provider,
            StrategyAction.ADJUST_PARAMS: self._execute_adjust_params,
            StrategyAction.CHANGE_APPROACH: self._execute_change_approach,
            StrategyAction.REQUEST_BOSS: self._execute_request_boss,
            StrategyAction.ABORT: self._execute_abort,
        }

        handler = strategy_map.get(strategy, self._execute_retry)
        result = await handler(record, ctx)

        # 记录经验
        if result.success:
            await self.recovery.record_lesson(
                record.id,
                f"Auto-recovery succeeded via {strategy.value}: {result.message}",
                True,
            )
        else:
            await self.recovery.record_lesson(
                record.id,
                f"Auto-recovery failed via {strategy.value}: {result.message}",
                False,
            )

        return result

    async def _execute_retry(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行重试策略。"""
        retry_count = record.retry_count + 1
        record.retry_count = retry_count

        record.strategy_action = StrategyAction.RETRY.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "retry_attempt": retry_count,
            "executed_at": datetime.now(UTC).isoformat(),
        }
        await self.session.commit()

        logger.info(
            "recovery_retry_executed",
            record_id=record.id,
            retry_count=retry_count,
            max_retries=record.max_retries,
        )

        return StrategyExecutionResult(
            success=True,
            action="retry",
            message=f"Retry #{retry_count} registered",
            retry_count=retry_count,
            details={"retry_count": retry_count, "max_retries": record.max_retries},
        )

    async def _execute_switch_agent(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行更换 Agent 策略。"""
        record.strategy_action = StrategyAction.SWITCH_AGENT.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "switch_agent",
            "executed_at": datetime.now(UTC).isoformat(),
            "note": "Agent switch requested — next execution will use a different agent type",
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=True,
            action="switch_agent",
            message="Agent switch requested for next execution",
            details={"strategy": "switch_agent"},
        )

    async def _execute_switch_provider(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行更换 Provider 策略。"""
        record.strategy_action = StrategyAction.SWITCH_PROVIDER.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "switch_provider",
            "executed_at": datetime.now(UTC).isoformat(),
            "note": "Provider switch requested — next execution will use a different LLM provider",
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=True,
            action="switch_provider",
            message="Provider switch requested for next execution",
            details={"strategy": "switch_provider"},
        )

    async def _execute_adjust_params(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行调整参数策略。"""
        adjusted_params = {
            "prev_temperature": context.get("temperature"),
            "prev_max_tokens": context.get("max_tokens"),
            "adjusted_temperature": min(0.7, (context.get("temperature", 0.7) or 0.7) * 0.8),
            "adjusted_max_tokens": min(
                4096, int((context.get("max_tokens", 2048) or 2048) * 1.5)
            ),
            "executed_at": datetime.now(UTC).isoformat(),
        }
        record.strategy_action = StrategyAction.ADJUST_PARAMS.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "adjust_params",
            **adjusted_params,
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=True,
            action="adjust_params",
            message="Parameters adjusted for next execution",
            details=adjusted_params,
        )

    async def _execute_change_approach(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行更换方案策略。"""
        record.strategy_action = StrategyAction.CHANGE_APPROACH.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "change_approach",
            "executed_at": datetime.now(UTC).isoformat(),
            "note": "Approach change requested — task execution strategy will be modified",
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=True,
            action="change_approach",
            message="Approach change registered for next execution",
            details={"strategy": "change_approach"},
        )

    async def _execute_request_boss(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行请求老板策略。"""
        record.threshold_exceeded = True
        record.boss_notified = True
        record.strategy_action = StrategyAction.REQUEST_BOSS.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "request_boss",
            "executed_at": datetime.now(UTC).isoformat(),
            "thresholds": self.recovery.SAFETY_THRESHOLDS,
            "retry_count": record.retry_count,
            "failure_category": record.failure_category,
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=True,
            action="request_boss",
            message="Boss notification sent — waiting for decision",
            details={"boss_notified": True, "threshold_exceeded": True},
        )

    async def _execute_abort(
        self, record: FailureRecordModel, context: Dict[str, Any]
    ) -> StrategyExecutionResult:
        """执行终止策略。"""
        record.strategy_action = StrategyAction.ABORT.value
        record.strategy_detail = {
            ** (record.strategy_detail or {}),
            "action": "abort",
            "executed_at": datetime.now(UTC).isoformat(),
            "reason": "Task aborted by recovery strategy — manual intervention required",
        }
        await self.session.commit()

        return StrategyExecutionResult(
            success=False,
            action="abort",
            message="Task aborted — manual intervention required",
            details={"aborted": True},
        )