"""
供应商数据验证器
Week 3 Day 1 - Supplier API Enhancement

提供供应商数据的验证规则，包括：
- 唯一性验证（名称、代码）
- 格式验证（邮箱、手机、网址、证书编号）
- 业务规则验证（有效期、必填字段等）
"""

import re
from typing import Optional, Dict, Any
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.models import Supplier, SupplierCertificate


class SupplierValidator:
    """供应商数据验证器"""
    
    # 正则表达式模式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?[0-9]{1,4}[-\s]?[0-9]{7,15}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    SUPPLIER_CODE_PATTERN = re.compile(r'^SUP[0-9]{4,8}$')
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def validate_unique_name(
        self,
        name: str,
        exclude_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        验证供应商名称唯一性
        
        Args:
            name: 供应商名称
            exclude_id: 排除的供应商ID（用于更新时）
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        query = select(Supplier).where(Supplier.name == name)
        if exclude_id:
            query = query.where(Supplier.id != exclude_id)
        
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return {
                "valid": False,
                "error": f"供应商名称 '{name}' 已存在（ID: {existing.id}）"
            }
        
        return {"valid": True, "error": None}
    
    async def validate_unique_code(
        self,
        code: str,
        exclude_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        验证供应商代码唯一性
        
        Args:
            code: 供应商代码
            exclude_id: 排除的供应商ID（用于更新时）
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        query = select(Supplier).where(Supplier.code == code)
        if exclude_id:
            query = query.where(Supplier.id != exclude_id)
        
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return {
                "valid": False,
                "error": f"供应商代码 '{code}' 已存在（ID: {existing.id}）"
            }
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_name_format(name: str) -> Dict[str, Any]:
        """
        验证供应商名称格式
        
        Args:
            name: 供应商名称
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if not name or not name.strip():
            return {"valid": False, "error": "供应商名称不能为空"}
        
        name_len = len(name.strip())
        if name_len < 2:
            return {"valid": False, "error": "供应商名称长度不能少于2个字符"}
        
        if name_len > 200:
            return {"valid": False, "error": "供应商名称长度不能超过200个字符"}
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_code_format(code: str) -> Dict[str, Any]:
        """
        验证供应商代码格式（SUP[0-9]{4,8}）
        
        Args:
            code: 供应商代码
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if not code or not code.strip():
            return {"valid": False, "error": "供应商代码不能为空"}
        
        if not SupplierValidator.SUPPLIER_CODE_PATTERN.match(code):
            return {
                "valid": False,
                "error": "供应商代码格式错误，正确格式：SUP + 4-8位数字（例如：SUP0001）"
            }
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_email_format(email: str) -> Dict[str, Any]:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if not email or not email.strip():
            return {"valid": True, "error": None}  # 邮箱可选
        
        if not SupplierValidator.EMAIL_PATTERN.match(email):
            return {"valid": False, "error": f"邮箱格式错误: {email}"}
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_phone_format(phone: str) -> Dict[str, Any]:
        """
        验证手机号格式（支持国际格式）
        
        Args:
            phone: 手机号
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if not phone or not phone.strip():
            return {"valid": True, "error": None}  # 手机号可选
        
        if not SupplierValidator.PHONE_PATTERN.match(phone):
            return {
                "valid": False,
                "error": f"手机号格式错误: {phone}，支持格式：+86-13800138000 或 13800138000"
            }
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_url_format(url: str) -> Dict[str, Any]:
        """
        验证网址格式
        
        Args:
            url: 网址
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if not url or not url.strip():
            return {"valid": True, "error": None}  # 网址可选
        
        if not SupplierValidator.URL_PATTERN.match(url):
            return {
                "valid": False,
                "error": f"网址格式错误: {url}，必须以 http:// 或 https:// 开头"
            }
        
        return {"valid": True, "error": None}
    
    @staticmethod
    def validate_certificate_expiry(
        issue_date: datetime,
        expiry_date: datetime
    ) -> Dict[str, Any]:
        """
        验证证书有效期
        
        Args:
            issue_date: 签发日期
            expiry_date: 过期日期
        
        Returns:
            验证结果字典 {"valid": bool, "error": Optional[str]}
        """
        if expiry_date <= issue_date:
            return {
                "valid": False,
                "error": "证书过期日期必须晚于签发日期"
            }
        
        if expiry_date < datetime.now(UTC):
            return {
                "valid": False,
                "error": f"证书已过期（过期日期: {expiry_date.strftime('%Y-%m-%d')}）"
            }
        
        return {"valid": True, "error": None}
    
    async def validate_supplier_data(
        self,
        data: Dict[str, Any],
        is_update: bool = False,
        supplier_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        验证供应商数据（综合验证）
        
        Args:
            data: 供应商数据字典
            is_update: 是否为更新操作
            supplier_id: 供应商ID（更新时使用）
        
        Returns:
            验证结果字典 {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        # 1. 名称验证
        if "name" in data:
            name_format = self.validate_name_format(data["name"])
            if not name_format["valid"]:
                errors.append(name_format["error"])
            else:
                # 唯一性验证
                exclude_id = supplier_id if is_update else None
                name_unique = await self.validate_unique_name(data["name"], exclude_id)
                if not name_unique["valid"]:
                    errors.append(name_unique["error"])
        
        # 2. 代码验证
        if "code" in data:
            code_format = self.validate_code_format(data["code"])
            if not code_format["valid"]:
                errors.append(code_format["error"])
            else:
                # 唯一性验证
                exclude_id = supplier_id if is_update else None
                code_unique = await self.validate_unique_code(data["code"], exclude_id)
                if not code_unique["valid"]:
                    errors.append(code_unique["error"])
        
        # 3. 邮箱验证
        if "email" in data and data["email"]:
            email_result = self.validate_email_format(data["email"])
            if not email_result["valid"]:
                errors.append(email_result["error"])
        
        # 4. 手机号验证
        if "phone" in data and data["phone"]:
            phone_result = self.validate_phone_format(data["phone"])
            if not phone_result["valid"]:
                errors.append(phone_result["error"])
        
        # 5. 网址验证
        if "website" in data and data["website"]:
            url_result = self.validate_url_format(data["website"])
            if not url_result["valid"]:
                errors.append(url_result["error"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
