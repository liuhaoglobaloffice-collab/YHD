"""
S6 系统监控 - 系统总览端点.

提供模块数据统计、版本、健康度等运维信息。
"""

from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src import __version__
from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.business.supplier.models import Supplier
from src.crm.models import Lead, SupplierAnalysisReport
from src.database.models import AIEmployeeModel, AiCostRecordModel, ProductModel
from src.evolve.models import EmployeeTemplate, EvolutionProposal, MetaKnowledge, SkillPack
from src.integrations.models import PlatformAccount, PlatformMessage
from src.identity.models import User
from src.site_os.models import KeywordRank, SitePage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


async def _count(model, session: AsyncSession) -> int:
    result = await session.execute(select(func.count(model.id)))
    return result.scalar_one() or 0


async def _count_owned(model, session: AsyncSession, column, user_ids) -> int:
    stmt = select(func.count(model.id)).where(column.in_(list(user_ids)))
    result = await session.execute(stmt)
    return result.scalar_one() or 0


def _visible_user_ids(user: User) -> set[int]:
    from src.identity.visibility import visible_user_ids

    return visible_user_ids(user)


@router.get("/overview")
async def system_overview(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("system", "read")),
):
    """系统总览：各模块数据量、版本与健康度（按登录账号可见范围统计业务数据）。"""
    owner_ids = _visible_user_ids(current_user)

    # 业务数据：按可见范围（owner 看自己，子账号看主账号+自己）
    counts = {
        "leads": await _count_owned(Lead, session, Lead.owner_user_id, owner_ids),
        "suppliers": await _count_owned(Supplier, session, Supplier.created_by, owner_ids),
        "supplier_reports": await _count_owned(
            SupplierAnalysisReport, session, SupplierAnalysisReport.created_by, owner_ids
        ),
        "platform_accounts": await _count_owned(
            PlatformAccount, session, PlatformAccount.owner_user_id, owner_ids
        ),
        "platform_messages": await _count_owned(
            PlatformMessage, session, PlatformMessage.owner_user_id, owner_ids
        ),
        "site_pages": await _count_owned(SitePage, session, SitePage.owner_user_id, owner_ids),
        "products": await _count_owned(ProductModel, session, ProductModel.created_by, owner_ids),
        "keyword_ranks": await _count_owned(
            KeywordRank, session, KeywordRank.owner_user_id, owner_ids
        ),
        "ai_calls": await _count_owned(
            AiCostRecordModel, session, AiCostRecordModel.user_id, owner_ids
        ),
    }
    # AI 成本汇总（可见范围内）
    cost_result = await session.execute(
        select(func.coalesce(func.sum(AiCostRecordModel.cost_usd), 0.0)).where(
            AiCostRecordModel.user_id.in_(list(owner_ids))
        )
    )
    counts["ai_cost_usd"] = round(float(cost_result.scalar_one() or 0.0), 6)
    # 系统级资产（团队/市场/知识）：全局共享，主/子账号一致
    counts.update(
        {
            "ai_employees": await _count(AIEmployeeModel, session),
            "employee_templates": await _count(EmployeeTemplate, session),
            "skill_packs": await _count(SkillPack, session),
            "meta_knowledge": await _count(MetaKnowledge, session),
            "evolution_proposals": await _count(EvolutionProposal, session),
        }
    )
    return {
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modules": counts,
        "total_records": sum(counts.values()),
        "scope": "sub" if current_user.account_type and current_user.account_type.value == "sub" else "owner",
        "status": "healthy",
    }


@router.get("/user-monitor")
async def user_monitor(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("system", "read")),
):
    """用户级监控面板：当前用户的资源用量和活动统计。"""
    from src.crm.models import Lead
    from src.database.models import AiCostRecordModel, TaskModel
    from src.integrations.models import PlatformMessage
    from src.site_os.models import SitePage

    uid = current_user.id

    # AI 调用统计
    cost_stmt = select(AiCostRecordModel).where(AiCostRecordModel.user_id == uid)
    cost_records = list((await session.execute(cost_stmt)).scalars().all())
    total_calls = len(cost_records)
    total_cost = sum(c.cost_usd or 0 for c in cost_records)
    total_tokens = sum(c.total_tokens or 0 for c in cost_records)
    failed_calls = sum(1 for c in cost_records if c.status == "failed")

    # 线索统计
    lead_stmt = select(Lead).where(Lead.owner_user_id == uid)
    leads = list((await session.execute(lead_stmt)).scalars().all())
    lead_count = len(leads)
    won_leads = sum(1 for l in leads if l.status.value == "won")

    # 任务统计
    task_stmt = select(TaskModel).where(TaskModel.creator_id == str(uid))
    tasks = list((await session.execute(task_stmt)).scalars().all())
    task_count = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "completed")

    # 消息统计
    msg_stmt = select(PlatformMessage).where(PlatformMessage.owner_user_id == uid)
    messages = list((await session.execute(msg_stmt)).scalars().all())
    msg_count = len(messages)
    sent_msgs = sum(1 for m in messages if m.direction.value == "outbound")
    received_msgs = sum(1 for m in messages if m.direction.value == "inbound")

    # 页面统计
    page_stmt = select(SitePage).where(SitePage.owner_user_id == uid)
    pages = list((await session.execute(page_stmt)).scalars().all())
    page_count = len(pages)
    published_pages = sum(1 for p in pages if p.status.value == "published")

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "account_type": current_user.account_type.value if current_user.account_type else "owner",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        },
        "ai_usage": {
            "total_calls": total_calls,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "failed_calls": failed_calls,
        },
        "business": {
            "leads": lead_count,
            "won_leads": won_leads,
            "tasks": task_count,
            "completed_tasks": completed_tasks,
        },
        "communication": {
            "total_messages": msg_count,
            "sent": sent_msgs,
            "received": received_msgs,
        },
        "content": {
            "pages": page_count,
            "published": published_pages,
        },
    }