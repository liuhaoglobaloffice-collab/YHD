"""
AI 成本追踪（V3 · 能量系统落地）.

记录每次 AI 任务执行的 Token 用量、估算成本与耗时，并支持聚合统计，
让主账号对 AI 员工的运行代价一目了然。

- estimate_cost(): 按模型单价估算成本（USD）
- record():        写入一条成本记录
- summary():       成本/请求数/Token/耗时聚合
- list_records():  最近记录列表
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AiCostRecordModel

logger = logging.getLogger(__name__)

# Token 单价表（USD / 1M tokens），近似主流价格，可按需更新
TOKEN_PRICE_PER_M = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4": (30.00, 60.00),
    "gpt-4-turbo": (10.00, 30.00),
    "qwen2.5:3b": (0.0, 0.0),  # 本地模型免费
    "qwen2.5:7b": (0.0, 0.0),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "gemini-pro": (1.25, 5.00),
    "gemini-1.5-pro": (1.25, 5.00),
    "deepseek-chat": (0.27, 1.10),
    "moonshot-v1-8k": (12.00, 12.00),
    "grok-beta": (5.00, 15.00),
}

# 未在表中的模型使用默认单价（分数精确到模型名前缀）
DEFAULT_PRICE_PER_M = (1.00, 3.00)


def _price_for(model: Optional[str]) -> tuple:
    """按模型名精确匹配，其次按前缀匹配。"""
    if not model:
        return DEFAULT_PRICE_PER_M
    key = model.strip().lower()
    if key in TOKEN_PRICE_PER_M:
        return TOKEN_PRICE_PER_M[key]
    for name, price in TOKEN_PRICE_PER_M.items():
        if key.startswith(name.lower()):
            return price
    return DEFAULT_PRICE_PER_M


def estimate_cost(model: Optional[str], input_tokens: int, output_tokens: int) -> float:
    """估算一次调用的成本（USD）。"""
    in_price, out_price = _price_for(model)
    return round((input_tokens * in_price + output_tokens * out_price) / 1_000_000, 6)


class CostTracker:
    """AI 成本追踪服务。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        user_id: int,
        provider: str,
        model: Optional[str],
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: Optional[float] = None,
        status: str = "success",
        employee_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> AiCostRecordModel:
        """写入一条成本记录。"""
        total = input_tokens + output_tokens
        cost = estimate_cost(model, input_tokens, output_tokens)
        rec = AiCostRecordModel(
            user_id=user_id,
            employee_id=employee_id,
            agent_type=agent_type,
            provider=(provider or "unknown").lower(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            meta=meta,
        )
        self.session.add(rec)
        await self.session.commit()
        await self.session.refresh(rec)
        return rec

    async def summary(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """成本聚合：累计成本/请求数/Token/平均耗时，及按 Provider 拆分。"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(AiCostRecordModel).where(
            AiCostRecordModel.user_id == user_id,
            AiCostRecordModel.created_at >= since,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())

        total_cost = sum(r.cost_usd or 0 for r in rows)
        total_requests = len(rows)
        total_tokens = sum(r.total_tokens or 0 for r in rows)
        latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
        failed = sum(1 for r in rows if r.status == "failed")

        by_provider: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            p = r.provider or "unknown"
            agg = by_provider.setdefault(
                p, {"requests": 0, "cost_usd": 0.0, "tokens": 0}
            )
            agg["requests"] += 1
            agg["cost_usd"] = round(agg["cost_usd"] + (r.cost_usd or 0), 6)
            agg["tokens"] += r.total_tokens or 0

        return {
            "days": days,
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency,
            "failed_requests": failed,
            "by_provider": by_provider,
        }

    async def list_records(
        self, user_id: int, limit: int = 50
    ) -> List[AiCostRecordModel]:
        """最近成本记录（时间倒序）。"""
        stmt = (
            select(AiCostRecordModel)
            .where(AiCostRecordModel.user_id == user_id)
            .order_by(AiCostRecordModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def monthly_usage(self, user_id: int) -> Dict[str, Any]:
        """当月（自然月）AI 用量：成本与调用次数。"""
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(AiCostRecordModel).where(
            AiCostRecordModel.user_id == user_id,
            AiCostRecordModel.created_at >= month_start,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return {
            "month": now.strftime("%Y-%m"),
            "cost_usd": round(sum(r.cost_usd or 0 for r in rows), 4),
            "calls": len(rows),
        }

    async def check_budget(self, user_id: int) -> Dict[str, Any]:
        """预算检查（V4）：返回该账号当月预算是否允许继续执行。

        - ai_budget_monthly 为 NULL → 不限
        - 当月已用 >= 预算 → allow=False（超限拦截）
        """
        from src.identity.models import User  # 局部导入避免循环依赖

        user = await self.session.get(User, user_id)
        budget = user.ai_budget_monthly if user else None

        if budget is None:
            return {
                "allow": True,
                "budget": None,
                "used_usd": 0.0,
                "calls": 0,
                "remaining_usd": None,
                "over_budget": False,
            }

        usage = await self.monthly_usage(user_id)
        used = usage.get("cost_usd", 0.0)
        return {
            "allow": not (budget is not None and used > budget),
            "budget": budget,
            "used_usd": used,
            "calls": usage.get("calls", 0),
            "remaining_usd": round(budget - used, 4),
            "over_budget": used > budget,
        }