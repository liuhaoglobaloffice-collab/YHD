"""
S6 安全加固 - 敏感数据脱敏工具

对 email / phone / whatsapp / wechat 等联系方式做脱敏，
防止敏感信息在接口响应中完整暴露（数据隐私合规）。
"""

import re
from typing import Any, Dict, Optional


def mask_email(email: Optional[str]) -> Optional[str]:
    """邮箱脱敏：abc***@example.com"""
    if not email:
        return email
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        shown = local[0] + "***"
    else:
        shown = local[:2] + "***"
    return f"{shown}@{domain}"


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """电话/手机号脱敏：+1 555 *** 0001"""
    if not phone:
        return phone
    digits = "".join(ch for ch in phone if ch.isdigit() or ch in "+")
    if len(digits) <= 4:
        return "***"
    return f"{phone[:4]}***{phone[-4:]}"


def mask_name(name: Optional[str]) -> Optional[str]:
    """联系人名称脱敏：张***（保留前1字）"""
    if not name:
        return name
    if len(name) <= 1:
        return name[0] + "***"
    return name[:1] + "***"


# 需要脱敏的字段映射：字段名 -> 脱敏函数
SENSITIVE_FIELDS = {
    "email": mask_email,
    "phone": mask_phone,
    "mobile": mask_phone,
    "whatsapp": mask_phone,
    "contact": mask_name,
}


def mask_dict(data: Dict[str, Any], sensitive: Optional[list] = None) -> Dict[str, Any]:
    """对字典中的敏感字段进行脱敏（原地拷贝）。"""
    result = dict(data)
    fields = sensitive if sensitive is not None else list(SENSITIVE_FIELDS.keys())
    for field in fields:
        mask_fn = SENSITIVE_FIELDS.get(field)
        if field in result and mask_fn:
            result[field] = mask_fn(result[field])
    return result


def redact_secrets(data: Any) -> Any:
    """深度过滤凭据字段（credentials/token/secret）。"""
    if isinstance(data, dict):
        return {
            k: ("***" if k in ("credentials", "access_token", "secret", "password", "api_key", "token") and v else redact_secrets(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [redact_secrets(d) for d in data]
    return data