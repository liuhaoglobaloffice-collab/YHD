"""
S2 多平台接入 API.

提供平台账号绑定、消息收发、联系人管理与多语言翻译端点。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.visibility import visible_user_ids
from src.integrations.models import (
    MessageDirection,
    MessageStatus,
    PlatformAccountStatus,
    PlatformType,
)
from src.integrations.service import PlatformService
from src.integrations.translation import LANGUAGE_LIST

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/platforms", tags=["platforms"])


# ==================== Schemas ====================


class AccountCreate(BaseModel):
    platform: PlatformType
    name: str = Field(..., min_length=1, max_length=255)
    account_id: str = Field(..., min_length=1, max_length=255)
    credentials: Optional[Dict[str, Any]] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    credentials: Optional[Dict[str, Any]] = None


class AccountOut(BaseModel):
    id: int
    platform: str
    name: str
    account_id: str
    status: str
    is_active: bool
    last_connected_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountListOut(BaseModel):
    accounts: List[AccountOut]
    total: int
    platforms: List[Dict[str, str]]


class SendMessageRequest(BaseModel):
    to_id: str = Field(..., min_length=1)
    to_name: Optional[str] = None
    content: str = Field(..., min_length=1)
    target_lang: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    platform: str
    account_id: int
    direction: str
    from_id: Optional[str] = None
    from_name: Optional[str] = None
    to_id: Optional[str] = None
    to_name: Optional[str] = None
    content: str
    translated_content: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    source_type: str = "MOCK"
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactOut(BaseModel):
    id: int
    platform: str
    remote_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    last_message_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = Field(..., min_length=2)


# ==================== Helpers ====================

PLATFORM_LABELS = {
    "whatsapp": "WhatsApp",
    "facebook": "Facebook / Messenger",
    "linkedin": "LinkedIn",
    "wechat": "企业微信",
}


def _serialize_account(acc) -> AccountOut:
    return AccountOut(
        id=acc.id,
        platform=acc.platform.value,
        name=acc.name,
        account_id=acc.account_id,
        status=acc.status.value,
        is_active=acc.is_active,
        last_connected_at=acc.last_connected_at,
        created_at=acc.created_at,
    )


def _serialize_message(msg) -> MessageOut:
    return MessageOut(
        id=msg.id,
        platform=msg.platform.value,
        account_id=msg.account_id,
        direction=msg.direction.value,
        from_id=msg.from_id,
        from_name=msg.from_name,
        to_id=msg.to_id,
        to_name=msg.to_name,
        content=msg.content,
        translated_content=msg.translated_content,
        source_lang=msg.source_lang,
        target_lang=msg.target_lang,
        source_type=getattr(msg, "source_type", "MOCK"),
        status=msg.status.value,
        created_at=msg.created_at,
    )


def _serialize_contact(c) -> ContactOut:
    return ContactOut(
        id=c.id,
        platform=c.platform.value,
        remote_id=c.remote_id,
        name=c.name,
        phone=c.phone,
        email=c.email,
        last_message_at=c.last_message_at,
    )


# ==================== 平台账号 ====================


@router.get("/accounts", response_model=AccountListOut)
async def list_accounts(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """列出当前用户的平台账号。"""
    service = PlatformService(session)
    accounts = await service.list_accounts(visible_user_ids(current_user))
    platforms = [
        {"value": p.value, "label": PLATFORM_LABELS[p.value]}
        for p in PlatformType
    ]
    return AccountListOut(
        accounts=[_serialize_account(a) for a in accounts],
        total=len(accounts),
        platforms=platforms,
    )


@router.post("/accounts", response_model=AccountOut, status_code=201)
async def create_account(
    request: AccountCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "create")),
):
    """绑定一个平台账号。"""
    service = PlatformService(session)
    try:
        account = await service.create_account(
            platform=request.platform.value,
            name=request.name,
            account_id=request.account_id,
            credentials=request.credentials,
            owner_user_id=current_user.id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await AuditService.log_success(
        session=session,
        action="bind_platform",
        resource_type="platform",
        user_id=current_user.id,
        resource_id=str(account.id),
        details={"platform": account.platform.value, "account_id": account.account_id},
    )
    return _serialize_account(account)


@router.delete("/accounts/{account_id}", status_code=200)
async def delete_account(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "delete")),
):
    """解绑平台账号。"""
    service = PlatformService(session)
    ok = await service.delete_account(account_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    return {"ok": True}


@router.patch("/accounts/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: int,
    request: AccountUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "update")),
):
    """更新平台账号名称或凭据。"""
    service = PlatformService(session)
    try:
        account = await service.update_account(
            account_id, current_user.id,
            name=request.name, credentials=request.credentials,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_account(account)


@router.post("/accounts/{account_id}/toggle", response_model=AccountOut)
async def toggle_account(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "update")),
):
    """切换平台账号启用/停用。"""
    service = PlatformService(session)
    try:
        account = await service.toggle_account(account_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_account(account)


@router.post("/accounts/{account_id}/test")
async def test_account(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """测试平台连接。"""
    service = PlatformService(session)
    try:
        return await service.test_connection(account_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 消息收发 ====================


@router.post("/accounts/{account_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    account_id: int,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "message_send")),
):
    """向平台联系人发送消息（可选自动翻译）。"""
    service = PlatformService(session)
    try:
        result = await service.send_message(
            account_id=account_id,
            owner_user_id=current_user.id,
            to_id=request.to_id,
            content=request.content,
            to_name=request.to_name,
            target_lang=request.target_lang,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 返回发出的消息记录
    from sqlalchemy import select
    from src.integrations.models import PlatformMessage

    stmt = select(PlatformMessage).where(PlatformMessage.id == result["message_id"])
    msg = (await session.execute(stmt)).scalar_one()
    return _serialize_message(msg)


@router.get("/accounts/{account_id}/messages", response_model=List[MessageOut])
async def list_messages(
    account_id: int,
    direction: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """查看平台账号消息记录。"""
    service = PlatformService(session)
    if await service.get_account(account_id, visible_user_ids(current_user)) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    messages = await service.list_messages(account_id, current_user.id)
    if direction:
        messages = [m for m in messages if m.direction.value == direction]
    return [_serialize_message(m) for m in messages]


@router.post("/accounts/{account_id}/receive", response_model=List[MessageOut])
async def receive_messages(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """拉取平台收件消息。"""
    service = PlatformService(session)
    if await service.get_account(account_id, {current_user.id}) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    messages = await service.receive_messages(account_id, current_user.id)
    return [_serialize_message(m) for m in messages]


@router.get("/accounts/{account_id}/messages/search", response_model=List[MessageOut])
async def search_messages(
    account_id: int,
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """搜索平台消息（按关键词）。"""
    service = PlatformService(session)
    if await service.get_account(account_id, {current_user.id}) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    messages = await service.search_messages(account_id, current_user.id, q)
    return [_serialize_message(m) for m in messages]


# ==================== 联系人 ====================


@router.get("/accounts/{account_id}/contacts", response_model=List[ContactOut])
async def list_contacts(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """查看平台联系人。"""
    service = PlatformService(session)
    if await service.get_account(account_id, visible_user_ids(current_user)) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    contacts = await service.list_contacts(account_id, current_user.id)
    from src.core.masking import mask_dict

    return [mask_dict(_serialize_contact(c).model_dump()) for c in contacts]


@router.post("/accounts/{account_id}/contacts/sync", response_model=Dict[str, int])
async def sync_contacts(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """从平台同步联系人。"""
    service = PlatformService(session)
    if await service.get_account(account_id, {current_user.id}) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    count = await service.sync_contacts(account_id, current_user.id)
    return {"synced": count}


# ==================== 多语言翻译 ====================


@router.get("/languages")
async def list_languages(
    _: User = Depends(get_current_user),
):
    """列出支持的语言。"""
    return {"languages": LANGUAGE_LIST}


@router.post("/translate")
async def translate(
    request: TranslateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "read")),
):
    """多语言自动翻译。"""
    service = PlatformService(session)
    try:
        result = await service.translator.translate(request.text, request.target_lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ==================== CRM 联动 ====================


@router.post("/accounts/{account_id}/sync-crm")
async def sync_platform_contacts_to_crm(
    account_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "write")),
):
    """将平台联系人同步为 CRM 线索。"""
    service = PlatformService(session)
    if await service.get_account(account_id, visible_user_ids(current_user)) is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    try:
        result = await service.sync_contacts_to_crm(account_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/messages/{message_id}/to-lead")
async def message_to_lead_activity(
    message_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("platform", "write")),
):
    """将平台消息转为 CRM 线索活动。"""
    service = PlatformService(session)
    try:
        result = await service.message_to_lead_activity(message_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
