"""
外贸报价单管理 API

提供报价单的 CRUD、状态流转、发送功能。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.crm.quotation import QuoteService, QuoteStatus
from src.identity.models import User
from src.identity.visibility import DataScopeFilter, visible_user_ids

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["quotes"])


# ==================== Schemas ====================


class QuoteItemCreate(BaseModel):
    product_name: str = Field(..., min_length=1)
    product_code: Optional[str] = None
    specification: Optional[str] = None
    unit: str = "件"
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    remark: Optional[str] = None


class QuoteCreate(BaseModel):
    lead_id: Optional[int] = None
    lead_name: str = Field(..., min_length=1)
    lead_company: Optional[str] = None
    lead_email: Optional[str] = None
    lead_phone: Optional[str] = None
    subject: str = Field(..., min_length=1)
    currency: str = "USD"
    discount: float = 0.0
    tax_rate: float = 0.0
    valid_days: int = 30
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    notes: Optional[str] = None
    items: List[QuoteItemCreate] = Field(..., min_length=1)


class QuoteStatusUpdate(BaseModel):
    status: str = Field(..., description="新状态: draft/pending_approval/approved/sent/following_up/accepted/rejected/expired")


class QuoteSendRequest(BaseModel):
    send_via: Optional[str] = Field(None, description="发送渠道: whatsapp/email")


class QuoteOut(BaseModel):
    id: int
    quote_number: str
    lead_id: Optional[int] = None
    lead_name: str
    lead_company: Optional[str] = None
    lead_email: Optional[str] = None
    lead_phone: Optional[str] = None
    status: str
    subject: str
    currency: str
    subtotal: float
    discount: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    valid_days: int
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    notes: Optional[str] = None
    items: List[Dict[str, Any]] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    sent_at: Optional[str] = None
    expires_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ==================== Endpoints ====================


@router.post("", response_model=Dict[str, Any], status_code=201)
async def create_quote(
    request: QuoteCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("crm", "write")),
):
    """创建报价单。"""
    svc = QuoteService(session)
    quote = await svc.create_quote(
        data=request.model_dump(),
        owner_user_id=current_user.id,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    return await svc.get_quote(quote.id, {current_user.id})


@router.get("")
async def list_quotes(
    status: Optional[str] = Query(None, description="状态筛选"),
    q: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("crm", "read")),
):
    """列出报价单。"""
    svc = QuoteService(session)
    return await svc.list_quotes(
        user_ids=visible_user_ids(current_user),
        status=status,
        keyword=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{quote_id}")
async def get_quote(
    quote_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("crm", "read")),
):
    """获取报价单详情。"""
    svc = QuoteService(session)
    result = await svc.get_quote(quote_id, visible_user_ids(current_user))
    if not result:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return result


@router.patch("/{quote_id}/status")
async def update_quote_status(
    quote_id: int,
    request: QuoteStatusUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("crm", "write")),
):
    """更新报价单状态。"""
    svc = QuoteService(session)
    try:
        quote = await svc.update_quote_status(quote_id, current_user.id, request.status)
        return await svc.get_quote(quote.id, {current_user.id})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{quote_id}/send")
async def send_quote(
    quote_id: int,
    request: QuoteSendRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("crm", "write")),
):
    """发送报价单给客户。"""
    svc = QuoteService(session)
    try:
        result = await svc.send_quote(quote_id, current_user.id, send_via=request.send_via)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))