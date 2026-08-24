"""
Week 3 Day 1 新功能测试
测试批量操作、高级搜索、导入/导出和数据验证功能
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.validators import SupplierValidator
from src.business.supplier.models import Supplier, SupplierStatus, BusinessType


class TestSupplierValidator:
    """测试供应商数据验证器"""
    
    @pytest.mark.asyncio
    async def test_validate_name_format(self):
        """测试名称格式验证"""
        # 正常名称
        result = SupplierValidator.validate_name_format("测试供应商有限公司")
        assert result["valid"] is True
        
        # 名称过短
        result = SupplierValidator.validate_name_format("A")
        assert result["valid"] is False
        assert "不能少于2个字符" in result["error"]
        
        # 名称过长
        result = SupplierValidator.validate_name_format("A" * 201)
        assert result["valid"] is False
        assert "不能超过200个字符" in result["error"]
        
        # 空名称
        result = SupplierValidator.validate_name_format("")
        assert result["valid"] is False
        assert "不能为空" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_code_format(self):
        """测试供应商代码格式验证"""
        # 正常代码
        result = SupplierValidator.validate_code_format("SUP0001")
        assert result["valid"] is True
        
        result = SupplierValidator.validate_code_format("SUP12345678")
        assert result["valid"] is True
        
        # 格式错误
        result = SupplierValidator.validate_code_format("ABC0001")
        assert result["valid"] is False
        assert "格式错误" in result["error"]
        
        result = SupplierValidator.validate_code_format("SUP001")  # 少于4位数字
        assert result["valid"] is False
        
        result = SupplierValidator.validate_code_format("SUP123456789")  # 超过8位数字
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_validate_email_format(self):
        """测试邮箱格式验证"""
        # 正常邮箱
        result = SupplierValidator.validate_email_format("test@example.com")
        assert result["valid"] is True
        
        # 格式错误
        result = SupplierValidator.validate_email_format("invalid-email")
        assert result["valid"] is False
        assert "邮箱格式错误" in result["error"]
        
        # 空邮箱（可选字段）
        result = SupplierValidator.validate_email_format("")
        assert result["valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_phone_format(self):
        """测试手机号格式验证"""
        # 正常手机号
        result = SupplierValidator.validate_phone_format("13800138000")
        assert result["valid"] is True
        
        result = SupplierValidator.validate_phone_format("+86-13800138000")
        assert result["valid"] is True
        
        # 格式错误
        result = SupplierValidator.validate_phone_format("123")
        assert result["valid"] is False
        assert "格式错误" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_unique_name(self, async_session: AsyncSession):
        """测试名称唯一性验证"""
        validator = SupplierValidator(async_session)
        
        # 创建测试供应商
        supplier = Supplier(
            name="唯一测试供应商",
            code="SUP9001",
            country="China",
            business_type=BusinessType.MANUFACTURER
        )
        async_session.add(supplier)
        await async_session.commit()
        
        # 测试重复名称
        result = await validator.validate_unique_name("唯一测试供应商")
        assert result["valid"] is False
        assert "已存在" in result["error"]
        
        # 测试新名称
        result = await validator.validate_unique_name("新供应商名称")
        assert result["valid"] is True
        
        # 测试更新时排除自身
        result = await validator.validate_unique_name("唯一测试供应商", exclude_id=supplier.id)
        assert result["valid"] is True


class TestBatchOperations:
    """测试批量操作"""
    
    @pytest.mark.asyncio
    async def test_batch_create(self, async_session: AsyncSession):
        """测试批量创建供应商"""
        crud = SupplierCRUD(async_session)
        
        suppliers_data = [
            {
                "name": f"批量测试供应商{i}",
                "code": f"SUP800{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            }
            for i in range(1, 6)
        ]
        
        result = await crud.batch_create(suppliers_data, validate=True)
        
        assert result["success"] == 5
        assert result["failed"] == 0
        assert len(result["ids"]) == 5
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_batch_create_with_validation_errors(self, async_session: AsyncSession):
        """测试批量创建时的验证错误"""
        crud = SupplierCRUD(async_session)
        
        suppliers_data = [
            {
                "name": "正常供应商",
                "code": "SUP8010",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            },
            {
                "name": "A",  # 名称过短
                "code": "SUP8011",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            },
            {
                "name": "正常供应商2",
                "code": "ABC123",  # 代码格式错误
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            }
        ]
        
        result = await crud.batch_create(suppliers_data, validate=True)
        
        assert result["success"] == 1
        assert result["failed"] == 2
        assert len(result["errors"]) == 2
    
    @pytest.mark.asyncio
    async def test_batch_update(self, async_session: AsyncSession):
        """测试批量更新供应商"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试供应商
        suppliers_data = [
            {
                "name": f"更新测试供应商{i}",
                "code": f"SUP820{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            }
            for i in range(1, 4)
        ]
        create_result = await crud.batch_create(suppliers_data, validate=False)
        
        # 批量更新
        updates = [
            {"id": supplier_id, "country": "USA"}
            for supplier_id in create_result["ids"]
        ]
        
        result = await crud.batch_update(updates, validate=False)
        
        assert result["success"] == 3
        assert result["failed"] == 0
        
        # 验证更新
        for supplier_id in create_result["ids"]:
            supplier = await crud.get_supplier(supplier_id)
            assert supplier.country == "USA"
    
    @pytest.mark.asyncio
    async def test_batch_delete(self, async_session: AsyncSession):
        """测试批量删除供应商"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试供应商
        suppliers_data = [
            {
                "name": f"删除测试供应商{i}",
                "code": f"SUP830{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER
            }
            for i in range(1, 4)
        ]
        create_result = await crud.batch_create(suppliers_data, validate=False)
        
        # 批量删除
        result = await crud.batch_delete(create_result["ids"])
        
        assert result["success"] == 3
        assert result["failed"] == 0
        
        # 验证删除
        for supplier_id in create_result["ids"]:
            supplier = await crud.get_supplier(supplier_id)
            assert supplier is None


class TestAdvancedSearch:
    """测试高级搜索"""
    
    @pytest.mark.asyncio
    async def test_advanced_search_by_name(self, async_session: AsyncSession):
        """测试按名称搜索"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试数据
        supplier = Supplier(
            name="高级搜索测试供应商",
            code="SUP9101",
            country="China",
            business_type=BusinessType.MANUFACTURER,
            registered_capital=5000000
        )
        async_session.add(supplier)
        await async_session.commit()
        
        # 搜索
        result = await crud.advanced_search(
            filters={"name": "高级搜索"},
            page=1,
            page_size=10
        )
        
        assert result["total"] >= 1
        assert len(result["items"]) >= 1
        assert any(s.name == "高级搜索测试供应商" for s in result["items"])
    
    @pytest.mark.asyncio
    async def test_advanced_search_by_capital_range(self, async_session: AsyncSession):
        """测试按注册资本范围搜索"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试数据
        suppliers_data = [
            {
                "name": f"资本测试{i}",
                "code": f"SUP911{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": i * 1000000
            }
            for i in range(1, 6)
        ]
        await crud.batch_create(suppliers_data, validate=False)
        
        # 搜索注册资本在2M-4M之间的供应商
        result = await crud.advanced_search(
            filters={"capital_min": 2000000, "capital_max": 4000000},
            page=1,
            page_size=10
        )
        
        assert result["total"] >= 3
        for supplier in result["items"]:
            if supplier.name.startswith("资本测试"):
                assert 2000000 <= supplier.registered_capital <= 4000000
    
    @pytest.mark.asyncio
    async def test_advanced_search_with_sorting(self, async_session: AsyncSession):
        """测试搜索结果排序"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试数据
        suppliers_data = [
            {
                "name": f"排序测试{i}",
                "code": f"SUP920{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": i * 1000000
            }
            for i in [3, 1, 2]
        ]
        await crud.batch_create(suppliers_data, validate=False)
        
        # 按注册资本升序
        result = await crud.advanced_search(
            filters={"name": "排序测试"},
            sort_by="registered_capital",
            sort_order="asc",
            page=1,
            page_size=10
        )
        
        capitals = [s.registered_capital for s in result["items"] if s.name.startswith("排序测试")]
        assert capitals == sorted(capitals)
        
        # 按注册资本降序
        result = await crud.advanced_search(
            filters={"name": "排序测试"},
            sort_by="registered_capital",
            sort_order="desc",
            page=1,
            page_size=10
        )
        
        capitals = [s.registered_capital for s in result["items"] if s.name.startswith("排序测试")]
        assert capitals == sorted(capitals, reverse=True)
