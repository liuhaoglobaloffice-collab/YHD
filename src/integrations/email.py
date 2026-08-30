"""
Email Service - SMTP 邮件发送（Lead 跟进通道）

设计原则（与 LeadAcquisitionEngine / PlatformMessage 一致）：
- 未配置 SMTP 凭证 → 诚实返回 NOT_CONFIGURED，绝不伪造发送成功
- 已配置 → 真实 SMTP 发送，返回 provider 消息响应
- 发送失败 → 返回 FAILED + 错误原因，由调用方落盘记录
- 使用 Python 标准库 smtplib（零新依赖），同步发送经 asyncio.to_thread 包装
"""

import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any, Dict, Optional

import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# SMTP 连接/发送超时（秒），防止阻塞请求过久
SMTP_TIMEOUT_SECONDS = 30


class EmailService:
    """SMTP 邮件发送服务。

    source_type 语义：
    - REAL          : SMTP 已配置且真实发送成功
    - NOT_CONFIGURED: SMTP 未配置（诚实降级，不发送）
    - FAILED        : SMTP 已配置但发送失败（错误已记录）
    """

    def __init__(self, settings: Optional[Any] = None):
        # settings 可注入以便测试；默认从当前进程环境读取
        self._settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        """SMTP 是否已配置（host + user + password 缺一不可）。"""
        s = self._settings
        return bool(s.smtp_host and s.smtp_user and s.smtp_password)

    def _not_configured_result(self, to: str, subject: str) -> Dict[str, Any]:
        logger.warning(
            "smtp_not_configured",
            hint="Set SMTP_HOST / SMTP_USER / SMTP_PASSWORD to enable real email sending",
        )
        return {
            "source_type": "NOT_CONFIGURED",
            "status": "not_configured",
            "to": to,
            "subject": subject,
            "message_id": None,
            "error": "SMTP 未配置（SMTP_HOST / SMTP_USER / SMTP_PASSWORD）",
        }

    def _send_sync(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """同步发送（在线程池中执行）。"""
        s = self._settings
        from_addr = s.smtp_from or s.smtp_user

        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        # 显式生成 Message-ID（smtplib 仅在真实发送时补齐，显式便于结果落盘追踪）
        msg["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1] if "@" in from_addr else "localhost")
        msg.set_content(body)

        try:
            if s.smtp_use_ssl:
                server: smtplib.SMTP = smtplib.SMTP_SSL(
                    s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
                )
            else:
                server = smtplib.SMTP(
                    s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
                )
            with server:
                if not s.smtp_use_ssl:
                    server.starttls()
                server.login(s.smtp_user, s.smtp_password)
                server.send_message(msg)
                # send_message 成功即接收方 SMTP 已接受；message-id 由本端生成
                message_id = msg.get("Message-ID")
                logger.info(
                    "smtp_email_sent",
                    from_addr=from_addr,
                    to=to,
                    subject=subject,
                    message_id=message_id,
                )
                return {
                    "source_type": "REAL",
                    "status": "sent",
                    "to": to,
                    "subject": subject,
                    "message_id": message_id,
                    "from": from_addr,
                    "error": None,
                }
        except (smtplib.SMTPException, OSError) as e:
            # smtplib.SMTPException 覆盖认证失败/拒收等；OSError 覆盖连接失败/超时
            logger.error("smtp_email_failed", to=to, subject=subject, error=str(e))
            return {
                "source_type": "FAILED",
                "status": "failed",
                "to": to,
                "subject": subject,
                "message_id": None,
                "error": f"SMTP 发送失败: {type(e).__name__}: {e}",
            }

    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """发送纯文本邮件。

        Returns:
            dict: source_type / status / to / subject / message_id / error
        """
        if not to or "@" not in to:
            return {
                "source_type": "FAILED",
                "status": "failed",
                "to": to,
                "subject": subject,
                "message_id": None,
                "error": f"收件地址无效: {to!r}",
            }
        if not self.is_configured:
            return self._not_configured_result(to, subject)
        # smtplib 为同步库，放线程池避免阻塞事件循环
        return await asyncio.to_thread(self._send_sync, to, subject, body)
