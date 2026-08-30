"""
Email Service - SMTP 邮件发送（Lead 跟进通道）

设计原则（与 LeadAcquisitionEngine / PlatformMessage 一致）：
- 未配置 SMTP 凭证 → 诚实返回 NOT_CONFIGURED，绝不伪造发送成功
- 已配置 → 真实 SMTP 发送，返回 provider 消息响应
- 发送失败 → 返回 FAILED + 错误原因，由调用方落盘记录
- 使用 Python 标准库 smtplib（零新依赖），同步发送经 asyncio.to_thread 包装
- SMTP_PROXY（可选）→ SOCKS5 / HTTP CONNECT 代理隧道，解决 SMTP 端口被墙阻断
  （smtplib 不读 HTTP_PROXY 环境变量，被墙网络必须显式配置隧道）
"""

import asyncio
import base64
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# SMTP 连接/发送超时（秒），防止阻塞请求过久
SMTP_TIMEOUT_SECONDS = 30


class _TunnelSMTP(smtplib.SMTP):
    """基于预建隧道 socket 的 SMTP 连接。

    smtplib 原生不支持代理；本类在建立隧道（SOCKS5 / HTTP CONNECT）
    后接管 socket 建立阶段，其余 SMTP 会话逻辑完全复用标准库实现。
    STARTTLS（587）由基类 starttls() 在隧道之上正常完成；
    SMTP_SSL（465）场景由调用方先在隧道上完成 TLS 包装再传入。
    """

    def __init__(self, tunneled_sock: socket.socket, host: str, timeout: float):
        self._tunnel_sock = tunneled_sock
        # host 非空触发 connect() → _get_socket() 返回预建隧道 socket
        super().__init__(host, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        return self._tunnel_sock


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """从 socket 精确读取 n 字节（不足即对端中断，抛 OSError）。"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError(f"代理连接中断（期望 {n} 字节，已收 {len(buf)}）")
        buf += chunk
    return buf


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

    # ==================== 代理隧道（P0: SMTP 被墙阻断的网络路径）====================

    def _socks5_tunnel(self, parsed, target_host: str, target_port: int) -> socket.socket:
        """SOCKS5 代理隧道（RFC 1928 / 1929 用户名密码认证）。"""
        proxy_port = parsed.port or 1080
        sock = socket.create_connection(
            (parsed.hostname, proxy_port), timeout=SMTP_TIMEOUT_SECONDS
        )
        try:
            # 1. 方法协商：无凭据仅声明匿名；带凭据声明"匿名 + 用户名密码"
            if parsed.username:
                sock.sendall(b"\x05\x02\x00\x02")
            else:
                sock.sendall(b"\x05\x01\x00")
            resp = _recv_exact(sock, 2)
            if resp[0] != 0x05:
                raise OSError(f"非 SOCKS5 代理响应: {resp!r}")
            method = resp[1]
            if method == 0x02:
                # RFC 1929 用户名/密码认证
                user = unquote(parsed.username or "").encode("utf-8")
                pwd = unquote(parsed.password or "").encode("utf-8")
                if len(user) > 255 or len(pwd) > 255:
                    raise OSError("SOCKS5 代理用户名/密码过长")
                sock.sendall(
                    b"\x01" + bytes([len(user)]) + user + bytes([len(pwd)]) + pwd
                )
                auth = _recv_exact(sock, 2)
                if auth[1] != 0x00:
                    raise OSError("SOCKS5 代理认证失败")
            elif method != 0x00:
                raise OSError(f"SOCKS5 代理拒绝可用认证方法: {method}")
            # 2. CONNECT 请求（域名地址类型 0x03，代理端解析 DNS）
            host_b = target_host.encode("ascii")
            if len(host_b) > 255:
                raise OSError("SMTP 主机名过长")
            sock.sendall(
                b"\x05\x01\x00\x03"
                + bytes([len(host_b)])
                + host_b
                + target_port.to_bytes(2, "big")
            )
            head = _recv_exact(sock, 4)
            if head[1] != 0x00:
                raise OSError(f"SOCKS5 CONNECT 被拒绝, code={head[1]}")
            # 3. 跳过绑定地址（IPv4 / 域名 / IPv6）
            atyp = head[3]
            if atyp == 0x01:
                _recv_exact(sock, 6)
            elif atyp == 0x03:
                ln = _recv_exact(sock, 1)[0]
                _recv_exact(sock, ln + 2)
            elif atyp == 0x04:
                _recv_exact(sock, 18)
            logger.info(
                "smtp_socks5_tunnel_ready",
                proxy=f"{parsed.hostname}:{proxy_port}",
                target=f"{target_host}:{target_port}",
            )
            return sock
        except Exception:
            sock.close()
            raise

    def _http_connect_tunnel(self, parsed, target_host: str, target_port: int) -> socket.socket:
        """HTTP CONNECT 代理隧道（兼容 v2rayN/Clash 等 Mixed 端口）。"""
        proxy_port = parsed.port or 8080
        sock = socket.create_connection(
            (parsed.hostname, proxy_port), timeout=SMTP_TIMEOUT_SECONDS
        )
        try:
            target = f"{target_host}:{target_port}"
            lines = [
                f"CONNECT {target} HTTP/1.1",
                f"Host: {target}",
                "Proxy-Connection: keep-alive",
            ]
            if parsed.username:
                cred = base64.b64encode(
                    f"{unquote(parsed.username)}:{unquote(parsed.password or '')}".encode()
                ).decode("ascii")
                lines.append(f"Proxy-Authorization: Basic {cred}")
            sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
            # 逐字节读取响应头直到空行：绝不读超（代理的 200 响应与后续
            # SMTP greeting 可能被 TCP 合并在同一数据段，多读会吞掉 greeting）
            buf = b""
            while not buf.endswith(b"\r\n\r\n"):
                chunk = sock.recv(1)
                if not chunk:
                    raise OSError("HTTP 代理连接中断")
                buf += chunk
                if len(buf) > 65536:
                    raise OSError("HTTP 代理响应头过大")
            status_line = buf.split(b"\r\n", 1)[0].decode("latin-1", "replace")
            if not status_line.endswith("200") and " 200 " not in status_line + " ":
                raise OSError(f"HTTP CONNECT 失败: {status_line}")
            logger.info(
                "smtp_http_connect_tunnel_ready",
                proxy=f"{parsed.hostname}:{proxy_port}",
                target=target,
            )
            return sock
        except Exception:
            sock.close()
            raise

    def _connect_via_proxy(self, proxy_url: str, s) -> smtplib.SMTP:
        """经代理隧道建立 SMTP 连接（含 465 SSL 场景的 TLS 包装）。"""
        parsed = urlparse(proxy_url)
        if parsed.scheme in ("socks5", "socks5h"):
            sock = self._socks5_tunnel(parsed, s.smtp_host, s.smtp_port)
        elif parsed.scheme in ("http", "https"):
            sock = self._http_connect_tunnel(parsed, s.smtp_host, s.smtp_port)
        else:
            raise ValueError(
                f"不支持的 SMTP_PROXY 类型: {parsed.scheme}://"
                "（支持 socks5:// 与 http://）"
            )
        try:
            if s.smtp_use_ssl:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=s.smtp_host)
            return _TunnelSMTP(sock, s.smtp_host, SMTP_TIMEOUT_SECONDS)
        except Exception:
            sock.close()
            raise

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
            proxy = getattr(s, "smtp_proxy", None)
            if proxy:
                server: smtplib.SMTP = self._connect_via_proxy(proxy, s)
            elif s.smtp_use_ssl:
                server = smtplib.SMTP_SSL(
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
        except (smtplib.SMTPException, OSError, ValueError) as e:
            # SMTPException 覆盖认证失败/拒收；OSError 覆盖连接/代理失败；
            # ValueError 覆盖 SMTP_PROXY 配置错误
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
