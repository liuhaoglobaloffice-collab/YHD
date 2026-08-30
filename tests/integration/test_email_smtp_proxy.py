"""SMTP 代理隧道集成测试 — EmailService SOCKS5 / HTTP CONNECT 隧道。

背景：smtplib 不读 HTTP_PROXY 环境变量，SMTP 端口被墙阻断时必须走显式隧道。

验证（本地真实 socket 全链路，非 mock 网络层）：
- SOCKS5 隧道（RFC 1928）+ STARTTLS 发送成功 → source_type=REAL
- SOCKS5 隧道（465 SSL）发送成功
- SOCKS5 用户名/密码认证（RFC 1929）成功 / 失败
- HTTP CONNECT 隧道发送成功（含 Basic Proxy-Authorization）
- 不支持的代理类型 → FAILED（诚实报错）
- 代理拒绝 CONNECT / 代理不可达 → FAILED
- 未配置代理 → 直连路径不受影响（不产生代理 CONNECT 请求）
- 代理 + SMTP 未配置 → NOT_CONFIGURED（代理不掩盖凭据缺失）
"""

import base64
import datetime
import ipaddress
import socket
import socketserver
import ssl
import threading
from functools import lru_cache
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.integrations.email import EmailService


# ==================== 自签证书（TLS 握手需要；smtplib 默认不校验）====================


@lru_cache(maxsize=1)
def _self_signed_cert():
    """生成测试用自签证书（进程内缓存）。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


# ==================== 模拟服务器：SOCKS5 / HTTP CONNECT + SMTP ====================


class _FakeProxySMTPHandler(socketserver.BaseRequestHandler):
    """单连接处理：代理握手（SOCKS5 或 HTTP CONNECT）→ SMTP 会话（可选 TLS）。

    direct_mode=True 时跳过代理握手（客户端直连 SMTP，先发 220 greeting）。
    """

    def _recv_exact(self, conn, n):
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("client closed early")
            buf += chunk
        return buf

    def _readline(self, conn):
        buf = b""
        while not buf.endswith(b"\r\n"):
            chunk = conn.recv(1)
            if not chunk:
                return None
            buf += chunk
        return buf

    def handle(self):
        conn = self.request
        server = self.server
        try:
            if server.direct_mode:
                if server.mode == "ssl":
                    conn = server.ssl_context.wrap_socket(conn, server_side=True)
                    server.tls_established = True
                self._handle_smtp(conn)
                return
            first = conn.recv(1)
            if first == b"\x05":
                ok = self._handle_socks5(conn)
            else:
                ok = self._handle_http_connect(conn, first)
            if not ok:
                return
            if server.mode == "ssl":
                conn = server.ssl_context.wrap_socket(conn, server_side=True)
                server.tls_established = True
            self._handle_smtp(conn)
        except (ConnectionError, OSError, ssl.SSLError, ValueError):
            pass  # 客户端断开等：测试服务器不抛错

    # ---------- SOCKS5 (RFC 1928 / 1929) ----------

    def _handle_socks5(self, conn):
        server = self.server
        nmethods = self._recv_exact(conn, 1)[0]
        methods = self._recv_exact(conn, nmethods)
        if server.socks_user and 0x02 in methods:
            conn.sendall(b"\x05\x02")
            self._recv_exact(conn, 1)  # auth version
            ulen = self._recv_exact(conn, 1)[0]
            user = self._recv_exact(conn, ulen)
            plen = self._recv_exact(conn, 1)[0]
            pwd = self._recv_exact(conn, plen)
            ok = (
                user == server.socks_user.encode()
                and pwd == server.socks_password.encode()
            )
            conn.sendall(b"\x01" + (b"\x00" if ok else b"\x01"))
            if not ok:
                server.auth_failures += 1
                return False
            server.authenticated = True
        else:
            conn.sendall(b"\x05\x00")
        # CONNECT 请求
        head = self._recv_exact(conn, 4)
        atyp = head[3]
        if atyp == 0x01:
            self._recv_exact(conn, 4)
            host = "<ipv4>"
        elif atyp == 0x03:
            ln = self._recv_exact(conn, 1)[0]
            host = self._recv_exact(conn, ln).decode()
        elif atyp == 0x04:
            self._recv_exact(conn, 16)
            host = "<ipv6>"
        else:
            return False
        port = int.from_bytes(self._recv_exact(conn, 2), "big")
        server.targets.append(f"{host}:{port}")
        if server.reject_connect:
            conn.sendall(b"\x05\x01\x00\x01" + b"\x00" * 4 + b"\x00\x00")
            return False
        conn.sendall(b"\x05\x00\x00\x01" + b"\x00" * 4 + b"\x00\x00")
        return True

    # ---------- HTTP CONNECT ----------

    def _handle_http_connect(self, conn, first_byte):
        server = self.server
        buf = first_byte
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return False
            buf += chunk
        request_line = buf.split(b"\r\n")[0].decode("latin-1")
        parts = request_line.split()
        target = parts[1] if len(parts) > 1 else "?"
        server.targets.append(target)
        server.connect_lines.append(request_line)
        for line in buf.split(b"\r\n"):
            if line.lower().startswith(b"proxy-authorization:"):
                server.auth_headers.append(line.decode("latin-1"))
        if server.reject_connect:
            conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return False
        conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        return True

    # ---------- SMTP ----------

    def _handle_smtp(self, conn):
        server = self.server
        conn.sendall(b"220 fake.smtp ESMTP ready\r\n")
        while True:
            line = self._readline(conn)
            if line is None:
                return
            cmd = line.upper()
            if cmd.startswith(b"EHLO"):
                caps = [b"250-fake.smtp", b"250-AUTH PLAIN LOGIN"]
                if server.mode == "starttls" and not server.tls_established:
                    caps.append(b"250 STARTTLS")
                else:
                    caps.append(b"250 8BITMIME")
                conn.sendall(b"\r\n".join(caps) + b"\r\n")
            elif cmd.startswith(b"STARTTLS"):
                conn.sendall(b"220 Go ahead\r\n")
                conn = server.ssl_context.wrap_socket(conn, server_side=True)
                server.tls_established = True
            elif cmd.startswith(b"AUTH"):
                conn.sendall(b"235 auth ok\r\n")
            elif cmd.startswith(b"MAIL FROM"):
                conn.sendall(b"250 ok\r\n")
            elif cmd.startswith(b"RCPT TO"):
                conn.sendall(b"250 ok\r\n")
            elif cmd.startswith(b"DATA"):
                conn.sendall(b"354 end with .\r\n")
                while True:
                    data_line = self._readline(conn)
                    if data_line is None:
                        return
                    if data_line.strip() == b".":
                        break
                    server.data_lines.append(data_line)
                server.mail_accepted += 1
                conn.sendall(b"250 accepted\r\n")
            elif cmd.startswith(b"QUIT"):
                conn.sendall(b"221 bye\r\n")
                return
            else:
                conn.sendall(b"250 ok\r\n")


class FakeProxySMTPServer(socketserver.ThreadingTCPServer):
    """SOCKS5 + HTTP CONNECT 双协议代理，隧道后为 SMTP 服务器。

    mode: "starttls"（587 明文 + STARTTLS 升级）或 "ssl"（465 直接 TLS）
    direct_mode: True 时不做代理握手（直连 SMTP 路径回归测试用）
    """

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        mode: str = "starttls",
        socks_user: str = "",
        socks_password: str = "",
        direct_mode: bool = False,
    ):
        self.mode = mode
        self.socks_user = socks_user
        self.socks_password = socks_password
        self.direct_mode = direct_mode
        self.targets = []
        self.connect_lines = []
        self.auth_headers = []
        self.data_lines = []
        self.tls_established = False
        self.authenticated = False
        self.auth_failures = 0
        self.mail_accepted = 0
        self.reject_connect = False

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_pem, key_pem = _self_signed_cert()
        import os
        import tempfile

        cert_dir = tempfile.mkdtemp(prefix="smtp_proxy_test_")
        cert_path = os.path.join(cert_dir, "cert.pem")
        key_path = os.path.join(cert_dir, "key.pem")
        with open(cert_path, "wb") as f:
            f.write(cert_pem)
        with open(key_path, "wb") as f:
            f.write(key_pem)
        self.ssl_context.load_cert_chain(cert_path, key_path)
        self.cert_path = cert_path
        self._cert_dir = cert_dir

        super().__init__(("127.0.0.1", 0), _FakeProxySMTPHandler)

    @property
    def port(self) -> int:
        return self.server_address[1]

    def cleanup(self):
        import shutil

        shutil.rmtree(self._cert_dir, ignore_errors=True)


def _start_server(**kwargs) -> FakeProxySMTPServer:
    server = FakeProxySMTPServer(**kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _stop_server(server: FakeProxySMTPServer):
    server.shutdown()
    server.server_close()
    server.cleanup()


@pytest.fixture
def fake_proxy_smtp():
    """默认 STARTTLS 模式（587）的模拟代理 + SMTP 服务器。"""
    server = _start_server(mode="starttls")
    yield server
    _stop_server(server)


def _settings(proxy, use_ssl: bool = False, host: str = "smtp.example.com", port=None):
    """构造带代理的 Settings 替身。"""
    return SimpleNamespace(
        smtp_host=host,
        smtp_port=port if port is not None else (465 if use_ssl else 587),
        smtp_user="boss@example.com",
        smtp_password="app-password-16",
        smtp_from="boss@example.com",
        smtp_use_ssl=use_ssl,
        smtp_proxy=proxy,
    )


# ==================== SOCKS5 隧道 ====================


class TestSocks5Proxy:
    """SOCKS5 隧道（无认证 / 用户名密码认证 / 465 SSL）。"""

    @pytest.mark.asyncio
    async def test_send_via_socks5_starttls(self, fake_proxy_smtp):
        """SOCKS5 隧道 + STARTTLS：真实发送成功，目标地址经代理 CONNECT。"""
        proxy = f"socks5://127.0.0.1:{fake_proxy_smtp.port}"
        service = EmailService(settings=_settings(proxy))
        result = await service.send_email(
            "buyer@example.com", "Inquiry: LED Panel", "Please quote 100pcs LED panel."
        )
        assert result["source_type"] == "REAL", result
        assert result["status"] == "sent"
        assert result["message_id"]
        # 隧道 CONNECT 的目标必须是 SMTP 服务器（代理端解析 DNS）
        assert fake_proxy_smtp.targets == ["smtp.example.com:587"]
        # STARTTLS 在隧道之上真实完成
        assert fake_proxy_smtp.tls_established
        # 邮件内容经隧道真实送达
        assert fake_proxy_smtp.mail_accepted == 1
        joined = b"".join(fake_proxy_smtp.data_lines)
        assert b"Subject: Inquiry: LED Panel" in joined

    @pytest.mark.asyncio
    async def test_send_via_socks5_ssl_port(self, monkeypatch):
        """SOCKS5 隧道 + 465 直接 TLS：握手顺序正确（先隧道后 TLS）。

        客户端 TLS 验证保持生产行为（ssl.create_default_context 严格校验）：
        通过 SSL_CERT_FILE 注入测试 CA + host 用证书 SAN 内的 localhost。
        """
        server = _start_server(mode="ssl")
        try:
            monkeypatch.setenv("SSL_CERT_FILE", server.cert_path)
            proxy = f"socks5://127.0.0.1:{server.port}"
            service = EmailService(settings=_settings(proxy, use_ssl=True, host="localhost"))
            result = await service.send_email(
                "buyer@example.com", "Quote", "Body text."
            )
            assert result["source_type"] == "REAL", result
            assert server.targets == ["localhost:465"]
            assert server.tls_established, "465 场景必须在隧道之上完成 TLS 握手"
            assert server.mail_accepted == 1
        finally:
            _stop_server(server)

    @pytest.mark.asyncio
    async def test_socks5_username_password_auth(self):
        """SOCKS5 RFC 1929 用户名/密码认证（代理 URL 内嵌凭据）。"""
        server = _start_server(
            mode="starttls", socks_user="proxyuser", socks_password="proxypass"
        )
        try:
            proxy = f"socks5://proxyuser:proxypass@127.0.0.1:{server.port}"
            service = EmailService(settings=_settings(proxy))
            result = await service.send_email("buyer@example.com", "Hi", "Hello.")
            assert result["source_type"] == "REAL", result
            assert server.authenticated, "代理必须完成用户名密码认证"
        finally:
            _stop_server(server)

    @pytest.mark.asyncio
    async def test_socks5_auth_rejected(self):
        """SOCKS5 认证失败 → FAILED（诚实报错，不伪造成功）。"""
        server = _start_server(
            mode="starttls", socks_user="proxyuser", socks_password="proxypass"
        )
        try:
            proxy = f"socks5://wrong:creds@127.0.0.1:{server.port}"
            service = EmailService(settings=_settings(proxy))
            result = await service.send_email("buyer@example.com", "Hi", "Hello.")
            assert result["source_type"] == "FAILED", result
            assert "认证失败" in result["error"]
            assert server.auth_failures == 1
        finally:
            _stop_server(server)


# ==================== HTTP CONNECT 隧道 ====================


class TestHttpConnectProxy:
    """HTTP CONNECT 隧道（兼容 v2rayN/Clash Mixed 端口）。"""

    @pytest.mark.asyncio
    async def test_send_via_http_connect(self, fake_proxy_smtp):
        """HTTP CONNECT 隧道：真实发送成功。"""
        proxy = f"http://127.0.0.1:{fake_proxy_smtp.port}"
        service = EmailService(settings=_settings(proxy))
        result = await service.send_email(
            "buyer@example.com", "Inquiry", "Body."
        )
        assert result["source_type"] == "REAL", result
        assert result["message_id"]
        assert fake_proxy_smtp.mail_accepted == 1
        assert fake_proxy_smtp.targets == ["smtp.example.com:587"]
        # CONNECT 请求行格式正确
        assert (
            fake_proxy_smtp.connect_lines[0]
            == "CONNECT smtp.example.com:587 HTTP/1.1"
        )

    @pytest.mark.asyncio
    async def test_http_connect_with_basic_auth(self):
        """HTTP CONNECT + Basic Proxy-Authorization（URL 内嵌凭据）。"""
        server = _start_server(mode="starttls")
        try:
            proxy = f"http://user:secret@127.0.0.1:{server.port}"
            service = EmailService(settings=_settings(proxy))
            result = await service.send_email("buyer@example.com", "Hi", "Body.")
            assert result["source_type"] == "REAL", result
            # 代理收到 Basic 凭据（user:secret 的 base64）
            expected = base64.b64encode(b"user:secret").decode()
            assert f"Proxy-Authorization: Basic {expected}" in server.auth_headers
        finally:
            _stop_server(server)


# ==================== 失败路径（诚实降级）====================


class TestProxyFailurePaths:
    """代理配置错误 / 代理拒绝 → FAILED；凭据缺失 → NOT_CONFIGURED。"""

    @pytest.mark.asyncio
    async def test_unsupported_proxy_scheme(self):
        """不支持的代理类型（如 ssh://）→ FAILED 且错误信息明确。"""
        service = EmailService(settings=_settings("ssh://127.0.0.1:2222"))
        result = await service.send_email("buyer@example.com", "Hi", "Body.")
        assert result["source_type"] == "FAILED", result
        assert "不支持" in result["error"]
        assert "ssh" in result["error"]

    @pytest.mark.asyncio
    async def test_proxy_rejects_connect(self, fake_proxy_smtp):
        """代理拒绝 CONNECT（SOCKS5 code != 0）→ FAILED。"""
        fake_proxy_smtp.reject_connect = True
        proxy = f"socks5://127.0.0.1:{fake_proxy_smtp.port}"
        service = EmailService(settings=_settings(proxy))
        result = await service.send_email("buyer@example.com", "Hi", "Body.")
        assert result["source_type"] == "FAILED", result
        assert "CONNECT" in result["error"] or "拒绝" in result["error"]

    @pytest.mark.asyncio
    async def test_proxy_unreachable(self):
        """代理不可达（端口无服务）→ FAILED（连接错误，不伪装成功）。"""
        # 找一个几乎必然无服务的端口：取刚关闭的 socket 绑定端口
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
        probe.close()
        service = EmailService(settings=_settings(f"socks5://127.0.0.1:{dead_port}"))
        result = await service.send_email("buyer@example.com", "Hi", "Body.")
        assert result["source_type"] == "FAILED", result
        assert result["error"]

    @pytest.mark.asyncio
    async def test_proxy_does_not_mask_missing_credentials(self, fake_proxy_smtp):
        """代理已配置但 SMTP 凭据缺失 → 仍为 NOT_CONFIGURED（代理不掩盖缺配置）。"""
        proxy = f"socks5://127.0.0.1:{fake_proxy_smtp.port}"
        settings = SimpleNamespace(
            smtp_host=None,
            smtp_port=587,
            smtp_user=None,
            smtp_password=None,
            smtp_from=None,
            smtp_use_ssl=False,
            smtp_proxy=proxy,
        )
        service = EmailService(settings=settings)
        result = await service.send_email("buyer@example.com", "Hi", "Body.")
        assert result["source_type"] == "NOT_CONFIGURED", result
        assert fake_proxy_smtp.targets == [], "未配置 SMTP 时不应发起任何代理连接"


# ==================== 直连路径回归（代理为空）====================


class TestDirectPathUnaffected:
    """未配置代理时保持既有直连行为（不产生代理握手）。"""

    @pytest.mark.asyncio
    async def test_no_proxy_uses_direct_smtp_starttls(self):
        """smtp_proxy=None → 直连 STARTTLS 发送成功，无代理握手。"""
        server = _start_server(mode="starttls", direct_mode=True)
        try:
            settings = _settings(
                proxy=None, host="127.0.0.1", port=server.port
            )
            service = EmailService(settings=settings)
            result = await service.send_email(
                "buyer@example.com", "Direct", "Body."
            )
            assert result["source_type"] == "REAL", result
            assert server.mail_accepted == 1
            assert server.targets == [], "直连不应产生代理 CONNECT 请求"
        finally:
            _stop_server(server)

    @pytest.mark.asyncio
    async def test_empty_proxy_string_is_direct(self):
        """smtp_proxy 为空字符串 → 等同直连。"""
        server = _start_server(mode="starttls", direct_mode=True)
        try:
            settings = _settings(
                proxy="", host="127.0.0.1", port=server.port
            )
            service = EmailService(settings=settings)
            result = await service.send_email(
                "buyer@example.com", "Direct", "Body."
            )
            assert result["source_type"] == "REAL", result
            assert server.targets == []
        finally:
            _stop_server(server)
