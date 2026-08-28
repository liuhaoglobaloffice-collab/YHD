"""
S2 多平台接入 - 统一收件箱 API

跨平台消息聚合、搜索、统计与统一回复。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.identity.models import User
from src.identity.visibility import DataScopeFilter, visible_user_ids
from src.integrations.service import PlatformService

router = APIRouter(prefix="/platforms/inbox", tags=["inbox"])


class InboxReplyRequest(BaseModel):
    content: str = Field(..., min_length=1, description="回复内容")
    target_lang: Optional[str] = Field(None, description="目标语言（可选翻译）")


@router.get("")
async def get_inbox(
    platform: Optional[str] = Query(None, description="平台筛选"),
    status: Optional[str] = Query(None, description="状态筛选: unread/inbound/outbound"),
    q: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """统一收件箱：跨平台消息聚合。"""
    svc = PlatformService(session)
    result = await svc.get_unified_inbox(
        user_ids=visible_user_ids(current_user),
        platform=platform,
        status=status,
        keyword=q,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/stats")
async def get_inbox_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收件箱统计：总消息数、今日消息、待回复、回复率。"""
    svc = PlatformService(session)
    return await svc.get_inbox_stats(user_ids=visible_user_ids(current_user))


@router.post("/{message_id}/reply")
async def reply_inbox_message(
    message_id: int,
    req: InboxReplyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从统一收件箱回复消息。"""
    svc = PlatformService(session)
    try:
        result = await svc.reply_inbox_message(
            message_id=message_id,
            owner_user_id=current_user.id,
            content=req.content,
            target_lang=req.target_lang,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))