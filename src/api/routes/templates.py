"""
S2 多平台接入 - 消息模板管理 API

提供预置消息模板的列表、详情、预览和发送功能。
真实模板发送需关联平台账号和凭据。
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.identity.models import User
from src.integrations.service import PlatformService
from src.integrations.templates import TemplateService

router = APIRouter(prefix="/platforms/templates", tags=["templates"])

template_svc = TemplateService()


class TemplateRenderRequest(BaseModel):
    template_id: str = Field(..., min_length=1)
    variables: Dict[str, str] = Field(default_factory=dict)


class TemplateSendRequest(BaseModel):
    template_id: str = Field(..., min_length=1)
    account_id: int = Field(..., gt=0)
    to_id: str = Field(..., min_length=1)
    to_name: Optional[str] = None
    variables: Dict[str, str] = Field(default_factory=dict)


@router.get("")
async def list_templates(
    platform: Optional[str] = Query(None, description="平台筛选"),
):
    """列出预置消息模板。"""
    return {"templates": template_svc.list_presets(platform)}


@router.get("/{template_id}")
async def get_template(template_id: str):
    """获取模板详情。"""
    tpl = template_svc.get_preset(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


@router.post("/render")
async def render_template(req: TemplateRenderRequest):
    """预览模板渲染结果。"""
    result = template_svc.render_template(req.template_id, req.variables)
    if result is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"rendered": result}


@router.post("/send")
async def send_template(
    req: TemplateSendRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送模板消息（通过平台账号发送）。

    渲染模板后调用平台 Provider 发送消息。
    """
    rendered = template_svc.render_template(req.template_id, req.variables)
    if rendered is None:
        raise HTTPException(status_code=404, detail="模板不存在")

    svc = PlatformService(session)
    result = await svc.send_message(
        account_id=req.account_id,
        owner_user_id=current_user.id,
        to_id=req.to_id,
        content=rendered,
        to_name=req.to_name,
    )
    return {
        "message_id": result["message_id"],
        "status": result["status"],
        "template_id": req.template_id,
        "rendered": rendered,
    }