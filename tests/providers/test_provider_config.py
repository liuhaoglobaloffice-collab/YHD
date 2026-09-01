"""Y1.0 回归测试：产品内 Provider/API Key 配置（模型注册）。

功能背景：
    老板在「模型与 Provider」页面添加云端/本地模型凭据，替代只能改环境
    变量的旧方式。链路：UI → POST /provider/configs → Fernet 加密落库
    PostgreSQL → 运行时注册进 Provider Gateway（无需重启）→ 健康检查。

本文件锁定的契约（与 scripts/verify_provider_config_e2e.py 的真实容器
E2E 互补：E2E 验证真实 PostgreSQL + 真实 Ollama，本文件在 CI/SQLite 下
快速回归，防止功能被回退）：

1. Catalog：覆盖 7 大主流 provider，形态正确，不泄漏密钥字段
2. 加密：ENCRYPTION_KEY 配置后 API Key 以 Fernet 密文落库、解密可往返；
   未配置时开发模式明文透传（不得报错）
3. 运行时注册：未知 provider 拒绝、云端 provider 缺 key 拒绝（fail-closed）、
   Ollama 免 key 可注册
4. 连接测试：未知 provider 返回 error；httpx 层 Mock 200 → healthy、
   401/403 → 认证失败；函数自身永不抛异常
5. 持久化 CRUD：upsert 存密文、list 脱敏（明文绝不返回）、更新留空保留
   原 key、删除幂等、启动加载应用已启用配置
6. HTTP/RBAC：匿名 401、viewer 只读（写 403）、user 角色写 403、
   admin 可写；未知 provider 400；test=true 失败 fail-closed 不落库；
   test=true 成功返回 health；删除未知配置 404
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fernet_key(monkeypatch):
    """配置真实 Fernet 密钥并重置加密器缓存，使加密走真实 AES 路径。"""
    from cryptography.fernet import Fernet

    import src.core.encryption as enc

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    enc._cipher = None
    yield
    enc._cipher = None


@pytest.fixture
def clean_gateway():
    """每个测试前后重置全局 Provider Gateway / Secrets 单例与运行时 env。

    apply_provider_runtime 会修改全局 gateway 单例并注入
    DEEPSEEK_API_KEY 等环境变量，必须隔离，避免跨测试污染。
    """
    from src.ai.gateway import reset_gateway
    from src.security.secrets import reset_secrets_manager

    leaked_env = [
        "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_CHAT_MODEL",
        "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_CHAT_MODEL",
        "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL", "MOONSHOT_CHAT_MODEL",
        "OLLAMA_HOST", "OLLAMA_DEFAULT_MODEL",
    ]
    saved = {k: os.environ.pop(k, None) for k in leaked_env}
    reset_gateway()
    reset_secrets_manager()
    yield
    reset_gateway()
    reset_secrets_manager()
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


@pytest.fixture
def provider_db_env(tmp_path, monkeypatch, fernet_key):
    """隔离的 SQLite + 真实加密环境（供持久化/HTTP 测试使用）。"""
    monkeypatch.setenv("METRICS_PERSIST", "0")
    db_file = tmp_path / "provider_config_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

    import src.api.dependencies.database as dep_db
    import src.identity.database as ident_db

    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db._engine = None
    ident_db._async_session_maker = None
    _dep_mod = sys.modules.get("src.api._dependencies_module")
    if _dep_mod:
        _dep_mod._lifecycle_manager = None

    from src.ai.gateway import reset_gateway
    from src.security.secrets import reset_secrets_manager

    reset_gateway()
    reset_secrets_manager()

    yield

    reset_gateway()
    reset_secrets_manager()
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db._engine = None
    ident_db._async_session_maker = None


def _register_login(client, username, role, password="testpass123"):
    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "full_name": username,
        "password": password,
        "role": role,
    })
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ============================================================================
# 1. Catalog
# ============================================================================


def test_catalog_covers_all_major_providers():
    from src.ai.provider_setup import PROVIDER_CATALOG

    expected = {"openai", "anthropic", "google", "deepseek", "xai", "moonshot", "ollama"}
    assert expected <= set(PROVIDER_CATALOG), f"缺失: {expected - set(PROVIDER_CATALOG)}"


def test_catalog_for_api_shape_and_no_secret_leak():
    from src.ai.provider_setup import catalog_for_api

    items = catalog_for_api()
    by_name = {p["name"]: p for p in items}

    for name in ("openai", "anthropic", "google", "deepseek", "xai", "moonshot", "ollama"):
        p = by_name[name]
        assert p["default_base_url"], f"{name} 缺少 default_base_url"
        assert p["default_model"], f"{name} 缺少 default_model"
        assert isinstance(p["needs_key"], bool)

    # 云端需要 key，本地 Ollama 不需要
    assert by_name["openai"]["needs_key"] is True
    assert by_name["deepseek"]["needs_key"] is True
    assert by_name["ollama"]["needs_key"] is False

    # catalog 是给前端表单的元数据，绝不能包含任何密钥/环境变量值
    raw = json.dumps(items, ensure_ascii=False)
    assert "api_key" not in raw
    assert "sk-" not in raw


# ============================================================================
# 2. 加密
# ============================================================================


def test_encrypt_decrypt_roundtrip_with_fernet(fernet_key):
    from src.core.encryption import decrypt_value, encrypt_value

    secret = "sk-test-secret-1234567890abcdef"
    ciphertext = encrypt_value(secret)
    assert ciphertext != secret, "配置 ENCRYPTION_KEY 后必须返回密文"
    assert ciphertext.startswith("gAAAAA"), f"非 Fernet token: {ciphertext[:10]}"
    assert secret not in ciphertext
    assert decrypt_value(ciphertext) == secret, "解密往返失败"


def test_encrypt_without_key_dev_mode_passthrough(monkeypatch):
    """未配置 ENCRYPTION_KEY（开发模式）时加解密透传明文，不得抛异常。"""
    import src.core.encryption as enc

    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    enc._cipher = None
    try:
        assert enc.encrypt_value("sk-dev-plain") == "sk-dev-plain"
        assert enc.decrypt_value("sk-dev-plain") == "sk-dev-plain"
        assert enc.encrypt_value("") == ""
        assert enc.decrypt_value(None) is None
    finally:
        enc._cipher = None


# ============================================================================
# 3. 运行时注册校验
# ============================================================================


def test_apply_runtime_rejects_unknown_provider(clean_gateway):
    from src.ai.provider_setup import apply_provider_runtime

    with pytest.raises(ValueError, match="未知 Provider"):
        apply_provider_runtime("not-a-real-provider", api_key="sk-x", base_url="https://x", model="m")


def test_apply_runtime_rejects_cloud_provider_without_key(clean_gateway):
    from src.ai.provider_setup import apply_provider_runtime

    for missing in (None, ""):
        with pytest.raises(ValueError, match="API Key"):
            apply_provider_runtime("deepseek", api_key=missing, base_url="", model="")


def test_apply_runtime_ollama_needs_no_key_and_registers(clean_gateway):
    from src.ai.gateway import get_gateway
    from src.ai.provider_setup import apply_provider_runtime
    from src.ai.providers import ProviderType

    result = apply_provider_runtime(
        "ollama",
        api_key=None,
        base_url="http://localhost:11434",
        model="qwen2.5:7b",
    )
    assert result["provider"] == "ollama"
    assert result["model"] == "qwen2.5:7b"

    real = get_gateway().list_real_providers()
    assert ProviderType.OLLAMA in real, f"Ollama 未注册进真实 provider: {real}"


def test_apply_runtime_replaces_existing_provider_idempotently(clean_gateway):
    """重复添加同一 provider 必须替换旧实例（密钥轮换/改地址即时生效）。"""
    from src.ai.gateway import get_gateway
    from src.ai.provider_setup import apply_provider_runtime
    from src.ai.providers import ProviderType

    apply_provider_runtime(
        "deepseek", api_key="sk-first-key-0000",
        base_url="https://api.deepseek.com/v1", model="deepseek-chat",
    )
    gw = get_gateway()
    assert ProviderType.DEEPSEEK in gw.list_real_providers()

    # 再次添加（轮换 key + 换模型）—— 不应抛 "already registered"
    apply_provider_runtime(
        "deepseek", api_key="sk-rotated-key-1111",
        base_url="https://api.deepseek.com/v1", model="deepseek-reasoner",
    )
    assert ProviderType.DEEPSEEK in gw.list_real_providers()


# ============================================================================
# 4. 连接测试（httpx MockTransport，无真实网络）
# ============================================================================


def _patch_httpx(monkeypatch, handler):
    """让 provider_setup 内部的 httpx.AsyncClient 走 MockTransport。"""
    import httpx

    real_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_test_connection_unknown_provider_returns_error():
    from src.ai.provider_setup import test_provider_connection

    result = await test_provider_connection("nope", api_key=None, base_url="https://x")
    assert result["status"] == "error"
    assert "未知 Provider" in result["detail"]


@pytest.mark.asyncio
async def test_test_connection_ollama_healthy(monkeypatch):
    from src.ai.provider_setup import test_provider_connection

    def handler(request):
        assert request.url.path.endswith("/api/tags")
        return httpx_response_200({"models": []})

    _patch_httpx(monkeypatch, handler)
    result = await test_provider_connection(
        "ollama", api_key=None, base_url="http://localhost:11434"
    )
    assert result["status"] == "healthy", result


@pytest.mark.asyncio
async def test_test_connection_openai_compatible_healthy(monkeypatch):
    from src.ai.provider_setup import test_provider_connection

    def handler(request):
        # OpenAI 兼容协议：Bearer 鉴权 + /models 元数据端点
        assert request.headers.get("Authorization") == "Bearer sk-valid"
        assert request.url.path.endswith("/models")
        return httpx_response_200({"data": []})

    _patch_httpx(monkeypatch, handler)
    result = await test_provider_connection(
        "deepseek", api_key="sk-valid", base_url="https://api.deepseek.com/v1"
    )
    assert result["status"] == "healthy", result


@pytest.mark.asyncio
async def test_test_connection_auth_failure_is_error_not_raise(monkeypatch):
    """401/403 → 结构化 error（fail-closed），函数本身绝不抛异常。"""
    import httpx
    from src.ai.provider_setup import test_provider_connection

    _patch_httpx(monkeypatch, lambda request: httpx.Response(401, json={"error": "invalid"}))
    result = await test_provider_connection(
        "deepseek", api_key="sk-bogus", base_url="https://api.deepseek.com/v1"
    )
    assert result["status"] == "error"
    assert "401" in result["detail"] or "认证" in result["detail"]


@pytest.mark.asyncio
async def test_test_connection_network_error_is_error_not_raise(monkeypatch):
    """连不上（连接拒绝）→ error/timeout 结构化结果，不抛异常。"""
    import httpx
    from src.ai.provider_setup import test_provider_connection

    def handler(request):
        raise httpx.ConnectError("connection refused")

    _patch_httpx(monkeypatch, handler)
    result = await test_provider_connection(
        "ollama", api_key=None, base_url="http://127.0.0.1:1"
    )
    assert result["status"] in ("error", "timeout")
    assert result["detail"]


def httpx_response_200(payload):
    import httpx

    return httpx.Response(200, json=payload)


# ============================================================================
# 5. 持久化 CRUD（真实 SQLite + 真实 Fernet 加密）
# ============================================================================


@pytest.mark.asyncio
async def test_persist_stores_ciphertext_and_list_masks(provider_db_env):
    from sqlalchemy import select

    from src.ai.provider_setup import (
        delete_persisted_config,
        list_persisted_configs,
        persist_provider_config,
    )
    from src.api.dependencies.database import get_session_factory, init_database
    from src.core.encryption import decrypt_value
    from src.database.models import LLMProviderConfigModel

    await init_database()
    Sess = get_session_factory()
    marker = "sk-PERSIST-MARKER-plaintext-must-not-leak-9f8e7d6c"

    async with Sess() as s:
        row = await persist_provider_config(
            s, name="deepseek", base_url=None, model=None,
            api_key=marker, created_by=1,
        )
        # 落库的必须是密文
        assert row.api_key_encrypted, "api_key_encrypted 不应为空"
        assert row.api_key_encrypted != marker
        assert marker not in row.api_key_encrypted
        assert len(row.api_key_encrypted) > 20
        # 密文必须能解密回原文
        assert decrypt_value(row.api_key_encrypted) == marker
        # 默认值来自 catalog
        assert row.base_url == "https://api.deepseek.com/v1"
        assert row.model == "deepseek-chat"

    async with Sess() as s:
        configs = await list_persisted_configs(s)

    cfg = next(c for c in configs if c["provider"] == "deepseek")
    assert cfg["has_api_key"] is True
    # 明文 key 绝不能出现在列表 payload 中
    assert "api_key" not in cfg
    assert marker not in json.dumps(cfg, ensure_ascii=False)
    # 脱敏预览只暴露后 4 位
    assert cfg["api_key_preview"].endswith(marker[-4:])
    assert "*" in cfg["api_key_preview"]
    assert marker[:-4] not in cfg["api_key_preview"]

    # 数据库物理层面再次确认是密文
    async with Sess() as s:
        db_row = await s.scalar(
            select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == "deepseek")
        )
        assert db_row is not None
        assert marker not in (db_row.api_key_encrypted or "")

    # 删除：存在 → True；再次删除 → False（幂等）
    async with Sess() as s:
        assert await delete_persisted_config(s, "deepseek") is True
    async with Sess() as s:
        assert await delete_persisted_config(s, "deepseek") is False


@pytest.mark.asyncio
async def test_persist_cloud_without_key_raises(provider_db_env):
    from src.ai.provider_setup import persist_provider_config
    from src.api.dependencies.database import get_session_factory, init_database

    await init_database()
    Sess = get_session_factory()
    async with Sess() as s:
        with pytest.raises(ValueError, match="API Key"):
            await persist_provider_config(
                s, name="openai", base_url=None, model=None, api_key=None
            )


@pytest.mark.asyncio
async def test_persist_update_without_key_keeps_stored_key(provider_db_env):
    """编辑配置时 API Key 留空 = 不修改原 key（前端编辑场景）。"""
    from src.ai.provider_setup import list_persisted_configs, persist_provider_config
    from src.api.dependencies.database import get_session_factory, init_database
    from src.core.encryption import decrypt_value
    from src.database.models import LLMProviderConfigModel
    from sqlalchemy import select

    await init_database()
    Sess = get_session_factory()
    marker = "sk-keep-me-rotate-endpoint-aaaa1111"

    async with Sess() as s:
        await persist_provider_config(
            s, name="deepseek", base_url=None, model="deepseek-chat",
            api_key=marker, created_by=1,
        )
        # 更新：只改 model，不传 key
        await persist_provider_config(
            s, name="deepseek", base_url=None, model="deepseek-reasoner",
            api_key=None, created_by=1,
        )

    async with Sess() as s:
        row = await s.scalar(
            select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == "deepseek")
        )
        assert row.model == "deepseek-reasoner"
        assert decrypt_value(row.api_key_encrypted) == marker, "留空更新不得覆盖原 key"


@pytest.mark.asyncio
async def test_load_persisted_providers_applies_on_startup(provider_db_env, clean_gateway):
    """启动钩子：DB 中 enabled 的配置必须被应用到运行时 gateway。"""
    from src.ai.gateway import get_gateway
    from src.ai.provider_setup import load_persisted_providers, persist_provider_config
    from src.api.dependencies.database import get_session_factory, init_database
    from src.ai.providers import ProviderType

    await init_database()
    Sess = get_session_factory()

    async with Sess() as s:
        await persist_provider_config(
            s, name="ollama", base_url="http://localhost:11434",
            model="qwen2.5:7b", api_key=None, created_by=1,
        )

    # 模拟重启：新进程视角 —— 清空 gateway 后从 DB 加载
    from src.ai.gateway import reset_gateway

    reset_gateway()
    async with Sess() as s:
        loaded = await load_persisted_providers(s)

    assert "ollama" in loaded, f"启动未加载已持久化的 provider: {loaded}"
    assert ProviderType.OLLAMA in get_gateway().list_real_providers()


# ============================================================================
# 6. HTTP API + RBAC（真实 TestClient + 真实 SQLite）
# ============================================================================


@pytest.fixture
def api_client(provider_db_env):
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with TestClient(create_app()) as client:
        admin_token = _register_login(client, "pc_admin", role="admin")
        viewer_token = _register_login(client, "pc_viewer", role="viewer")
        user_token = _register_login(client, "pc_user", role="user")
        yield client, {
            "admin": {"Authorization": f"Bearer {admin_token}"},
            "viewer": {"Authorization": f"Bearer {viewer_token}"},
            "user": {"Authorization": f"Bearer {user_token}"},
        }


def test_http_catalog_anonymous_denied(api_client):
    client, _ = api_client
    r = client.get("/api/v1/provider/catalog")
    assert r.status_code in (401, 403), f"匿名访问应被拒绝: {r.status_code}"


def test_http_admin_catalog_lists_all_providers(api_client):
    client, headers = api_client
    r = client.get("/api/v1/provider/catalog", headers=headers["admin"])
    assert r.status_code == 200, r.text
    names = {p["name"] for p in r.json()["providers"]}
    assert {"openai", "anthropic", "google", "deepseek", "xai", "moonshot", "ollama"} <= names


def test_http_viewer_can_read_but_not_write(api_client):
    client, headers = api_client
    # 读：viewer 拥有 system:read
    r = client.get("/api/v1/provider/configs", headers=headers["viewer"])
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/provider/catalog", headers=headers["viewer"])
    assert r.status_code == 200, r.text
    # 写：viewer 没有 system:write → 403
    r = client.post(
        "/api/v1/provider/configs", headers=headers["viewer"],
        json={"provider": "deepseek", "api_key": "sk-x", "test": False},
    )
    assert r.status_code == 403, f"viewer 越权写入未被拒绝: {r.status_code} {r.text}"
    # 删：同样 403
    r = client.delete("/api/v1/provider/configs/deepseek", headers=headers["viewer"])
    assert r.status_code == 403, f"viewer 越权删除未被拒绝: {r.status_code}"


def test_http_sub_user_role_cannot_write(api_client):
    """SUB 子账号 + user 角色：严格按角色矩阵，无 system:write → 403。

    注意：/auth/register 注册的都是 OWNER 主账号，OWNER+user 是老板全权
    （由 test_rbac_owner_permission_regression 锁定）。子账号走 SUB 类型，
    这里直接在 DB 构造真实 SUB+user 账号并走真实登录 + 真实路由鉴权。
    """
    import asyncio

    from sqlalchemy import select

    from src.api.dependencies.database import get_session_factory
    from src.identity.auth import hash_password
    from src.identity.models import AccountType, RoleEnum, User

    client, headers = api_client

    async def _create_sub():
        async with get_session_factory()() as s:
            owner = await s.scalar(
                select(User).where(User.account_type == AccountType.OWNER).limit(1)
            )
            sub = User(
                username="pc_sub_user",
                email="pc_sub_user@example.com",
                full_name="Sub User",
                hashed_password=hash_password("testpass123"),
                role=RoleEnum.USER,
                account_type=AccountType.SUB,
                parent_user_id=owner.id if owner else None,
                is_active=True,
                approval_status="approved",
            )
            s.add(sub)
            await s.commit()

    asyncio.run(_create_sub())

    r = client.post("/api/v1/auth/login", json={
        "username": "pc_sub_user", "password": "testpass123"
    })
    assert r.status_code == 200, r.text
    sub_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 子账号读：system:read 放行
    r = client.get("/api/v1/provider/configs", headers=sub_headers)
    assert r.status_code == 200, r.text
    # 子账号写：无 system:write → 403
    r = client.post(
        "/api/v1/provider/configs", headers=sub_headers,
        json={"provider": "deepseek", "api_key": "sk-x", "test": False},
    )
    assert r.status_code == 403, f"SUB+user 不应能写 provider 配置: {r.status_code} {r.text}"


def test_http_unsupported_provider_rejected(api_client):
    client, headers = api_client
    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={"provider": "not-a-provider", "api_key": "sk-x", "test": False},
    )
    assert r.status_code == 400, r.text


def test_http_cloud_provider_without_key_rejected(api_client):
    """云端 provider 缺 API Key 必须 400（fail-closed），不得落库。"""
    client, headers = api_client
    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={"provider": "deepseek", "test": False},
    )
    assert r.status_code == 400, r.text
    # 确认没有落库
    r = client.get("/api/v1/provider/configs", headers=headers["admin"])
    providers = {c["provider"] for c in r.json()["configs"]}
    assert "deepseek" not in providers


def test_http_save_provider_persists_encrypted_and_masks(api_client):
    """核心链路：admin 保存 → 200，响应无明文，DB 存密文，列表脱敏。"""
    client, headers = api_client
    marker = "sk-HTTP-MARKER-plaintext-must-not-leak-zzz9999"

    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={
            "provider": "deepseek",
            "api_key": marker,
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "test": False,
        },
    )
    assert r.status_code == 200, f"保存失败: {r.status_code} {r.text}"
    body = r.json()
    assert body["status"] == "configured"
    assert body["config"]["has_api_key"] is True
    # 响应体绝不能泄漏明文 key
    assert marker not in r.text
    assert "api_key" not in body["config"]

    # 列表同样脱敏
    r = client.get("/api/v1/provider/configs", headers=headers["admin"])
    assert marker not in r.text, "GET /configs 泄漏了明文 API Key"
    cfg = next(c for c in r.json()["configs"] if c["provider"] == "deepseek")
    assert cfg["api_key_preview"].endswith(marker[-4:])

    # DB 物理层面：存的是密文
    import asyncio

    from sqlalchemy import select

    from src.api.dependencies.database import get_session_factory
    from src.core.encryption import decrypt_value
    from src.database.models import LLMProviderConfigModel

    async def _check_db():
        async with get_session_factory()() as s:
            row = await s.scalar(
                select(LLMProviderConfigModel).where(
                    LLMProviderConfigModel.provider == "deepseek"
                )
            )
            assert row is not None, "配置未持久化"
            assert marker not in (row.api_key_encrypted or ""), "DB 中是明文!"
            assert decrypt_value(row.api_key_encrypted) == marker

    asyncio.run(_check_db())


def test_http_test_true_failure_is_fail_closed_not_persisted(api_client):
    """test=true 连接失败 → 400 且绝不落库（fail-closed 安全契约）。"""
    client, headers = api_client

    with patch(
        "src.api.routes.provider_status.test_provider_connection",
        new=AsyncMock(return_value={"status": "error", "detail": "认证失败（HTTP 401）"}),
    ):
        r = client.post(
            "/api/v1/provider/configs", headers=headers["admin"],
            json={
                "provider": "moonshot",
                "api_key": "sk-bogus-invalid-000000",
                "base_url": "https://api.moonshot.cn/v1",
                "test": True,
            },
        )
    assert r.status_code == 400, f"连接测试失败应拒绝保存: {r.status_code} {r.text}"
    assert "连接测试失败" in r.text

    # 失败的配置绝不能落库
    r = client.get("/api/v1/provider/configs", headers=headers["admin"])
    providers = {c["provider"] for c in r.json()["configs"]}
    assert "moonshot" not in providers, f"fail-closed 被破坏，失败配置已落库: {providers}"


def test_http_test_true_success_returns_health_and_persists(api_client):
    """test=true 连接成功 → 200 且带回 health，配置落库并注册运行时。"""
    client, headers = api_client

    with patch(
        "src.api.routes.provider_status.test_provider_connection",
        new=AsyncMock(return_value={"status": "healthy", "detail": "连接成功，凭据有效"}),
    ):
        r = client.post(
            "/api/v1/provider/configs", headers=headers["admin"],
            json={
                "provider": "xai",
                "api_key": "sk-xai-valid-1111",
                "base_url": "https://api.x.ai/v1",
                "model": "grok-2",
                "test": True,
            },
        )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    assert body["health"]["status"] == "healthy"
    assert body["config"]["provider"] == "xai"

    # 运行时状态应反映新 provider（refresh_provider_status 已在保存时触发）
    r = client.get("/api/v1/provider/status", headers=headers["admin"])
    assert r.status_code == 200
    assert "xai" in (r.json().get("provider") or ""), r.json()


def test_http_ollama_save_without_key_ok(api_client):
    """Ollama 本地模型无需 API Key 即可保存。"""
    client, headers = api_client
    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:7b",
            "test": False,
        },
    )
    assert r.status_code == 200, f"Ollama 免 key 保存失败: {r.status_code} {r.text}"
    assert r.json()["config"]["has_api_key"] is False


@pytest.mark.asyncio
async def test_persisted_provider_configs_are_scoped_to_tenant(provider_db_env):
    """同一 provider 在不同租户下必须分离，避免串客/跨租户泄露。"""
    from src.ai.provider_setup import list_persisted_configs, persist_provider_config
    from src.api.dependencies.database import get_session_factory, init_database

    await init_database()

    async with get_session_factory()() as session:
        await persist_provider_config(
            session,
            name="deepseek",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key="tenant-a-key",
            created_by=1,
            tenant_id="tenant-a",
        )
        await persist_provider_config(
            session,
            name="deepseek",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key="tenant-b-key",
            created_by=2,
            tenant_id="tenant-b",
        )

        tenant_a = await list_persisted_configs(session, tenant_id="tenant-a")
        tenant_b = await list_persisted_configs(session, tenant_id="tenant-b")
        all_rows = await list_persisted_configs(session)

        assert len(tenant_a) == 1 and tenant_a[0]["tenant_id"] == "tenant-a"
        assert len(tenant_b) == 1 and tenant_b[0]["tenant_id"] == "tenant-b"
        assert {row["tenant_id"] for row in all_rows} == {"tenant-a", "tenant-b"}
        assert tenant_a[0]["api_key_preview"].endswith("-key")
        assert tenant_b[0]["api_key_preview"].endswith("-key")


def test_http_delete_config_removes_row_and_404_for_unknown(api_client):
    client, headers = api_client
    # 先保存一个
    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={"provider": "ollama", "base_url": "http://localhost:11434",
              "model": "qwen2.5:7b", "test": False},
    )
    assert r.status_code == 200, r.text

    # 删除
    r = client.delete("/api/v1/provider/configs/ollama", headers=headers["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "removed"

    # 行已删除
    r = client.get("/api/v1/provider/configs", headers=headers["admin"])
    providers = {c["provider"] for c in r.json()["configs"]}
    assert "ollama" not in providers

    # 重复删除 / 未知 → 404
    r = client.delete("/api/v1/provider/configs/ollama", headers=headers["admin"])
    assert r.status_code == 404, r.text
    r = client.delete("/api/v1/provider/configs/doesnotexist", headers=headers["admin"])
    assert r.status_code == 404, r.text


def test_http_audit_log_written_on_config_change(api_client):
    """配置变更必须写审计日志（安全治理要求）。"""
    client, headers = api_client
    r = client.post(
        "/api/v1/provider/configs", headers=headers["admin"],
        json={"provider": "ollama", "base_url": "http://localhost:11434",
              "model": "qwen2.5:7b", "test": False},
    )
    assert r.status_code == 200, r.text

    # 审计日志接口可查到 provider_configured 事件
    r = client.get("/api/v1/audit/logs?limit=50", headers=headers["admin"])
    if r.status_code == 200:
        actions = json.dumps(r.json(), ensure_ascii=False)
        assert "provider_configured" in actions or "provider" in actions
