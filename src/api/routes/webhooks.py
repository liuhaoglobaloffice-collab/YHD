"""
S2 多平台接入 - Webhook API 端点

接收外部平台（WhatsApp / Facebook / 企业微信）的回调推送。
每个平台需要:
  - POST: 接收消息回调
  - GET: 平台验证（WhatsApp / Facebook 要求）
"""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.integrations.webhook import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ==================== WhatsApp Webhook ====================


@router.post("/whatsapp/{account_id}")
async def whatsapp_webhook_receive(
    account_id: int,
    body: dict,
    session: AsyncSession = Depends(get_db),
):
    """接收 WhatsApp Cloud API 的消息回调。"""
    svc = WebhookService(session)
    count = await svc.process_whatsapp(account_id, body)
    logger.info("webhook_whatsapp_received account_id=%s count=%s", account_id, count)
    return {"status": "ok", "received": count}


@router.get("/whatsapp/{account_id}")
async def whatsapp_webhook_verify(
    account_id: int,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp Webhook 验证端点（Meta 平台要求）。

    配置 Webhook 时，Meta 会发送 GET 请求验证端点所有权。
    """
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook 验证失败")


# ==================== Facebook Messenger Webhook ====================


@router.post("/facebook/{account_id}")
async def facebook_webhook_receive(
    account_id: int,
    body: dict,
    session: AsyncSession = Depends(get_db),
):
    """接收 Facebook Messenger 的消息回调。"""
    svc = WebhookService(session)
    count = await svc.process_facebook(account_id, body)
    logger.info("webhook_facebook_received account_id=%s count=%s", account_id, count)
    return {"status": "ok", "received": count}


@router.get("/facebook/{account_id}")
async def facebook_webhook_verify(
    account_id: int,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Facebook Messenger Webhook 验证端点。"""
    expected_token = os.getenv("FACEBOOK_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook 验证失败")


# ==================== 企业微信回调 ====================


@router.post("/wechat/{account_id}")
async def wechat_webhook_receive(
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """接收企业微信的回调消息。

    企业微信回调支持 XML 和 JSON 格式，此处解析 JSON。
    """
    svc = WebhookService(session)
    body = await request.json()
    count = await svc.process_wechat(account_id, body)
    logger.info("webhook_wechat_received account_id=%s count=%s", account_id, count)
    return {"status": "ok", "received": count}