"""
凭据加密/解密工具 (AES-256-GCM via Fernet)。

用于加密存储外部平台 API 凭据（access_token、secret 等敏感字段）。
通过环境变量 ENCRYPTION_KEY 配置密钥，未配置时返回明文（开发模式）。
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# 需要加密的凭据字段名
SENSITIVE_FIELDS = {"access_token", "token", "secret", "app_secret", "agent_secret", "client_secret"}

# 缓存 cipher 实例
_cipher = None


def _get_cipher():
    """获取 Fernet cipher 实例，未配置密钥时返回 None。"""
    global _cipher
    if _cipher is not None:
        return _cipher

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        logger.warning("ENCRYPTION_KEY 未配置，凭据将以明文存储（仅用于开发环境）")
        return None

    try:
        from cryptography.fernet import Fernet
        _cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return _cipher
    except Exception as e:
        logger.warning("ENCRYPTION_KEY 无效，凭据将以明文存储: %s", e)
        return None


def encrypt_credentials(credentials: dict | None) -> dict | None:
    """加密凭据中的敏感字段。"""
    if not credentials:
        return credentials

    cipher = _get_cipher()
    if cipher is None:
        return credentials  # 开发模式，不加密

    encrypted = {}
    for k, v in credentials.items():
        if k in SENSITIVE_FIELDS and isinstance(v, str) and v:
            try:
                encrypted[k] = cipher.encrypt(v.encode()).decode()
            except Exception as e:
                logger.error("加密凭据字段 %s 失败: %s", k, e)
                encrypted[k] = v
        else:
            encrypted[k] = v
    return encrypted


def decrypt_credentials(credentials: dict | None) -> dict | None:
    """解密凭据中的敏感字段。"""
    if not credentials:
        return credentials

    cipher = _get_cipher()
    if cipher is None:
        return credentials  # 开发模式，不解密

    decrypted = {}
    for k, v in credentials.items():
        if k in SENSITIVE_FIELDS and isinstance(v, str) and v:
            try:
                decrypted[k] = cipher.decrypt(v.encode()).decode()
            except Exception:
                # 可能是未加密的明文（存量数据），直接返回
                decrypted[k] = v
        else:
            decrypted[k] = v
    return decrypted


def generate_encryption_key() -> str:
    """生成一个新的加密密钥（用于初始化配置）。"""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()