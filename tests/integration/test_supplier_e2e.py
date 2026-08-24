"""
Week 3 Day 2 - Supplier全流程集成测试
端到端测试场景：模拟完整的供应商管理业务流程
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import Supplier, SupplierStatus, BusinessType
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.import_export import SupplierImportExport


class TestSupplierE2EWorkflow:
    """端到端业务流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_supplier_onboarding_workflow(self, async_session: AsyncSession):
        """
        测试完整的供应商入驻流程
        
        流程：创建 → 添加联系人 → 添加证书 → 风险评估 → 激活
        """
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 步骤1: 创建供应商（初始状态：PENDING）
        supplier_data = {
            "name": "端到端测试供应商",
            "legal_name": "端到端测试供应商有限公司",
            "code": "SUP1001",
            "country": "China",
            "city": "Shenzhen",
            "address": "深圳市南山区科技园",
            "business_type": BusinessType.MANUFACTURER,
            "product_category": "电子元器件",
            "industry": "电子制造",
            "established_date": datetime(2020, 1, 1),
            "registered_capital": 10000000,
            "employee_count": 500,
            "annual_revenue": 50000000,
            "phone": "+86-755-12345678",
            "email": "contact@e2etest.com",
            "website": "https://www.e2etest.com",
            "status": SupplierStatus.PENDING,
        }
        
        supplier = await crud.create_supplier(
            name=supplier_data["name"],
            country=supplier_data["country"],
            product_category=supplier_data["product_category"],
            **{k:v for k,v in supplier_data.items() if k not in ["name","country","product_category"]}
        )
        assert supplier.id is not None
        assert supplier.status == SupplierStatus.PENDING
        
        # 步骤2: 添加联系人
        contact_data = {
            "name": "张三",
            "position": "总经理",
            "department": "管理部",
            "phone": "+86-13800138000",
            "email": "zhangsan@e2etest.com",
            "is_primary": True,
        }
        
        contact = await crud.add_contact(supplier.id, contact_data)
        assert contact.id is not None
        assert contact.is_primary is True
        
        # 步骤3: 添加证书
        certificate_data = {
            "certificate_type": "BUSINESS_LICENSE",
            "certificate_name": "营业执照",
            "certificate_number": "BL123456789",
            "issuing_authority": "深圳市市场监督管理局",
            "issuing_country": "China",
            "issue_date": datetime(2020, 1, 1),
            "expiry_date": datetime(2030, 1, 1),
            "is_verified": True,
        }
        
        certificate = await crud.add_certificate(supplier.id, certificate_data)
        assert certificate.id is not None
        
        # 步骤4: 执行风险评估
        risk_assessment = await risk_agent.assess_risk(supplier_id=supplier.id)
        assert risk_assessment is not None
        assert "risk_level" in risk_assessment
        assert "risk_score" in risk_assessment
        
        # 步骤5: 激活供应商
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.ACTIVE})
        
        # 验证最终状态
        final_supplier = await crud.get_supplier(supplier.id)
        assert final_supplier.status == SupplierStatus.ACTIVE
        
        # 验证关联数据
        contacts = await crud.get_contacts(supplier.id)
        assert len(contacts) == 1
        
        certificates = await crud.get_certificates(supplier.id)
        assert len(certificates) == 1
        
        # Risk assessment completed
    
    @pytest.mark.asyncio
    async def test_supplier_data_migration_workflow(self, async_session: AsyncSession):
        """
        测试供应商数据迁移流程
        
        流程：批量导入 → 数据验证 → 风险评估 → 批量激活
        """
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 步骤1: 批量创建供应商
        suppliers_data = [
            {
                "name": f"迁移测试供应商{i}",
                "code": f"SUP200{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": 1000000 * i,
                "status": SupplierStatus.PENDING,
            }
            for i in range(1, 6)
        ]
        
        batch_result = await crud.batch_create(suppliers_data, validate=True)
        assert batch_result["success"] == 5
        assert batch_result["failed"] == 0
        
        created_ids = batch_result["ids"]
        
        # 步骤2: 批量风险评估
        for supplier_id in created_ids:
            await risk_agent.assess_risk(supplier_id=supplier_id)
        
        # 步骤3: 批量激活（仅低风险供应商）
        updates = []
        for supplier_id in created_ids:
            supplier = await crud.get_supplier(supplier_id)
            latest_assessment = await risk_agent.get_latest_assessment(supplier_id)
            if latest_assessment and latest_assessment.risk_score >= 60:  # 低风险
                updates.append({"id": supplier_id, "status": SupplierStatus.ACTIVE})
        
        if updates:
            update_result = await crud.batch_update(updates, validate=False)
            assert update_result["success"] > 0
        
        # 验证结果
        for supplier_id in created_ids:
            supplier = await crud.get_supplier(supplier_id)
            assert supplier is not None
    
    @pytest.mark.asyncio
    async def test_supplier_offboarding_workflow(self, async_session: AsyncSession):
        """
        测试供应商下线流程
        
        流程：停用 → 最终风险评估 → 归档/删除
        """
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 创建测试供应商
        supplier_data = {
            "name": "下线测试供应商",
            "code": "SUP3001",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
            "status": SupplierStatus.ACTIVE,
        }
        
        supplier = await crud.create_supplier(
            name=supplier_data["name"],
            country=supplier_data["country"],
            product_category=supplier_data["product_category"],
            **{k:v for k,v in supplier_data.items() if k not in ["name","country","product_category"]}
        )
        
        # 步骤1: 停用供应商
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.INACTIVE})
        updated_supplier = await crud.get_supplier(supplier.id)
        assert updated_supplier.status == SupplierStatus.INACTIVE
        
        # 步骤2: 最终风险评估
        final_assessment = await risk_agent.assess_risk(supplier_id=supplier.id)
        assert final_assessment is not None
        
        # 步骤3: 删除供应商
        await crud.delete_supplier(supplier.id)
        
        # 验证删除
        deleted_supplier = await crud.get_supplier(supplier.id)
        assert deleted_supplier is None
    
    @pytest.mark.asyncio
    async def test_supplier_search_and_filter_workflow(self, async_session: AsyncSession):
        """
        测试供应商搜索和筛选流程
        
        流程：创建多个供应商 → 高级搜索 → 筛选 → 导出
        """
        crud = SupplierCRUD(async_session)
        importer_exporter = SupplierImportExport(async_session)
        
        # 创建测试数据
        suppliers_data = [
            {
                "name": f"搜索测试{country}供应商{i}",
                "code": f"SUP400{i}",
                "country": country,
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": capital,
                "status": SupplierStatus.ACTIVE,
            }
            for i, (country, capital) in enumerate([
                ("China", 5000000),
                ("China", 10000000),
                ("USA", 15000000),
                ("USA", 20000000),
                ("Germany", 25000000),
            ], start=1)
        ]
        
        batch_result = await crud.batch_create(suppliers_data, validate=False)
        assert batch_result["success"] == 5
        
        # 步骤1: 按国家搜索
        china_results = await crud.advanced_search(
            filters={"country": "China"},
            page=1,
            page_size=10
        )
        china_count = sum(1 for s in china_results["items"] if s.name.startswith("搜索测试China"))
        assert china_count >= 2
        
        # 步骤2: 按注册资本范围搜索
        capital_results = await crud.advanced_search(
            filters={"capital_min": 10000000, "capital_max": 20000000},
            page=1,
            page_size=10
        )
        assert capital_results["total"] >= 3
        
        # 步骤3: 组合搜索（国家 + 资本范围）
        combined_results = await crud.advanced_search(
            filters={
                "country": "USA",
                "capital_min": 15000000,
            },
            page=1,
            page_size=10
        )
        usa_high_capital = sum(
            1 for s in combined_results["items"]
            if s.name.startswith("搜索测试USA") and s.registered_capital >= 15000000
        )
        assert usa_high_capital >= 2
        
        # 步骤4: 导出筛选结果
        export_filters = {"country": "China"}
        exported_data = await importer_exporter.export_suppliers(
            filters=export_filters,
            file_type="csv"
        )
        assert exported_data is not None
        assert len(exported_data) > 0


class TestSupplierBusinessRules:
    """业务规则验证测试"""
    
    @pytest.mark.asyncio
    async def test_supplier_status_transitions(self, async_session: AsyncSession):
        """测试供应商状态转换规则"""
        crud = SupplierCRUD(async_session)
        
        # 创建供应商（PENDING）
        supplier_data = {
            "name": "状态转换测试供应商",
            "code": "SUP5001",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
            "status": SupplierStatus.PENDING,
        }
        
        supplier = await crud.create_supplier(
            name=supplier_data["name"],
            country=supplier_data["country"],
            product_category=supplier_data["product_category"],
            **{k:v for k,v in supplier_data.items() if k not in ["name","country","product_category"]}
        )
        assert supplier.status == SupplierStatus.PENDING
        
        # PENDING → ACTIVE（正常流程）
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.ACTIVE})
        supplier = await crud.get_supplier(supplier.id)
        assert supplier.status == SupplierStatus.ACTIVE
        
        # ACTIVE → INACTIVE（暂停合作）
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.INACTIVE})
        supplier = await crud.get_supplier(supplier.id)
        assert supplier.status == SupplierStatus.INACTIVE
        
        # INACTIVE → ACTIVE（恢复合作）
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.ACTIVE})
        supplier = await crud.get_supplier(supplier.id)
        assert supplier.status == SupplierStatus.ACTIVE
        
        # ACTIVE → BLACKLIST（发现问题）
        await crud.update_supplier(supplier.id, {"status": SupplierStatus.BLACKLIST})
        supplier = await crud.get_supplier(supplier.id)
        assert supplier.status == SupplierStatus.BLACKLIST
    
    @pytest.mark.asyncio
    async def test_supplier_risk_score_impact(self, async_session: AsyncSession):
        """测试风险评分对业务决策的影响"""
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 创建高风险供应商（低注册资本、短历史）
        high_risk_supplier = await crud.create_supplier({
            "name": "高风险测试供应商",
            "code": "SUP5101",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
            "registered_capital": 500000,  # 低资本
            "established_date": datetime.utcnow() - timedelta(days=180),  # 成立半年
            "has_iso9001": False,
            "has_iso14001": False,
            "status": SupplierStatus.PENDING,
        })
        
        # 创建低风险供应商（高注册资本、长历史、认证齐全）
        low_risk_supplier = await crud.create_supplier({
            "name": "低风险测试供应商",
            "code": "SUP5102",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
            "registered_capital": 50000000,  # 高资本
            "established_date": datetime.utcnow() - timedelta(days=3650),  # 成立10年
            "has_iso9001": True,
            "has_iso14001": True,
            "cooperation_years": 5,
            "status": SupplierStatus.PENDING,
        })
        
        # 风险评估
        high_risk_result = await risk_agent.assess_risk(supplier_id=high_risk_supplier.id)
        low_risk_result = await risk_agent.assess_risk(supplier_id=low_risk_supplier.id)
        
        # 验证风险评分差异
        assert high_risk_result["risk_score"] < low_risk_result["risk_score"]
        
        # 业务规则：只激活低风险供应商
        if low_risk_result["risk_score"] >= 60:
            await crud.update_supplier(low_risk_supplier.id, {"status": SupplierStatus.ACTIVE})
        
        if high_risk_result["risk_score"] < 60:
            # 高风险供应商保持PENDING或拒绝
            pass
        
        # 验证最终状态
        final_low_risk = await crud.get_supplier(low_risk_supplier.id)
        final_high_risk = await crud.get_supplier(high_risk_supplier.id)
        
        # 低风险供应商应该被激活
        if low_risk_result["risk_score"] >= 60:
            assert final_low_risk.status == SupplierStatus.ACTIVE
        
        # 高风险供应商应该保持PENDING
        if high_risk_result["risk_score"] < 60:
            assert final_high_risk.status == SupplierStatus.PENDING
