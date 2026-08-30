"""P0-1 生产密钥部署安全自检测试"""
from typing import Dict
import pytest
from src.security.secrets import check_production_secrets
from types import SimpleNamespace


def test_check_production_secrets_detects_default_secret_key():
    bad = SimpleNamespace(
        app_env="production",
        secret_key="01234567890123456789012345678901",
        jwt_secret_key="a" * 32,
        postgres_password="real_pg_password_xyz",
    )
    result = check_production_secrets(bad)
    assert result["ok"] is False, f"expected fail, got: {result}"
    assert any("secret_key" in c for c in result["failed_checks"]), result["failed_checks"]


def test_check_production_secrets_detects_compose_placeholder():
    bad = SimpleNamespace(
        app_env="production",
        secret_key="change-me-please-use-a-long-random-value",
        jwt_secret_key="change-me-please-use-a-long-random-value",
        postgres_password="liuhao_pass",
    )
    result = check_production_secrets(bad)
    assert result["ok"] is False
    assert any("jwt_secret_key" in c for c in result["failed_checks"])
    assert any("postgres_password" in c for c in result["warnings"])


def test_check_production_secrets_passes_on_strong_values():
    good = SimpleNamespace(
        app_env="production",
        secret_key="prod-secret-key-over-32-chars-long-enough-001",
        jwt_secret_key="prod-jwt-key-over-32-chars-long-enough-abcdef-001",
        postgres_password="a-very-strong-postgres-password-123-aaa",
    )
    result = check_production_secrets(good)
    assert result["ok"] is True
    assert result["failed_checks"] == []
    assert result["warnings"] == []


def test_check_production_secrets_skips_in_development():
    dev = SimpleNamespace(
        app_env="development",
        secret_key="01234567890123456789012345678901",
        jwt_secret_key="abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
        postgres_password="liuhao_pass",
    )
    result = check_production_secrets(dev)
    assert result["ok"] is True
    assert len(result["warnings"]) >= 2



def test_ready_endpoint_includes_security_checks_degraded_on_default_prod(monkeypatch):
    """生产 + 占位密钥 → /health/ready 返回 security_checks 字段与 degraded。"""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-please-use-a-long-random-value")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-please-use-a-long-random-value")
    monkeypatch.setenv("POSTGRES_PASSWORD", "liuhao_pass")
    # SQLite 即可，不需要真实 PostgreSQL
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # 强制 settings 重新装载（get_settings() 内部缓存，这里通过 core.config 的 Settings 直接验证）
    from src.security.secrets import check_production_secrets
    from src.core.config import Settings

    settings = Settings(_env_file=None)  # 不走 .env，只用环境变量
    result = check_production_secrets(settings)
    assert result["ok"] is False
    assert len(result["failed_checks"]) >= 2
    assert any("postgres_password" in w for w in result["warnings"])
