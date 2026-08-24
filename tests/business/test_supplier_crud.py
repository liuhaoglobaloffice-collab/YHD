"""
供应商CRUD服务单元测试
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import (
    SupplierStatus,
    BusinessType,
    CertificateType,
    RiskLevel
)


@pytest.fixture
async def supplier_crud(async_session: AsyncSession):
    """供应商CRUD fixture"""
    return SupplierCRUD(async_session)


@pytest.fixture
async def sample_supplier(supplier_crud: SupplierCRUD):
    """创建示例供应商"""
    supplier = await supplier_crud.create_supplier(
        name="Test Supplier Co., Ltd.",
        legal_name="Test Supplier Legal Name",
        code="SUP-001",
        country="China",
        city="Shenzhen",
        product_category="Electronics",
        business_type=BusinessType.MANUFACTURER,
        employee_count=500,
        annual_revenue=10000000.0,
        status=SupplierStatus.ACTIVE
    )
    return supplier


class TestSupplierCRUD:
    """供应商主表CRUD测试"""
    
    async def test_create_supplier(self, supplier_crud: SupplierCRUD):
        """测试创建供应商"""
        supplier = await supplier_crud.create_supplier(
            name="New Supplier",
            country="USA",
            product_category="Machinery"
        )
        
        assert supplier.id is not None
        assert supplier.name == "New Supplier"
        assert supplier.country == "USA"
        assert supplier.status == SupplierStatus.PENDING
        assert supplier.created_at is not None
    
    async def test_get_supplier(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试获取供应商"""
        supplier = await supplier_crud.get_supplier(sample_supplier.id)
        
        assert supplier is not None
        assert supplier.id == sample_supplier.id
        assert supplier.name == sample_supplier.name
    
    async def test_get_supplier_not_found(self, supplier_crud: SupplierCRUD):
        """测试获取不存在的供应商"""
        supplier = await supplier_crud.get_supplier(99999)
        assert supplier is None
    
    async def test_get_supplier_by_code(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试通过编码获取供应商"""
        supplier = await supplier_crud.get_supplier_by_code("SUP-001")
        
        assert supplier is not None
        assert supplier.code == "SUP-001"
        assert supplier.name == sample_supplier.name
    
    async def test_list_suppliers(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试列出供应商"""
        suppliers = await supplier_crud.list_suppliers(limit=10)
        
        assert len(suppliers) > 0
        assert any(s.id == sample_supplier.id for s in suppliers)
    
    async def test_list_suppliers_with_filters(
        self, 
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试带筛选条件的供应商列表"""
        # 按状态筛选
        active_suppliers = await supplier_crud.list_suppliers(
            status=SupplierStatus.ACTIVE
        )
        assert all(s.status == SupplierStatus.ACTIVE for s in active_suppliers)
        
        # 按国家筛选
        china_suppliers = await supplier_crud.list_suppliers(country="China")
        assert all(s.country == "China" for s in china_suppliers)
        
        # 按业务类型筛选
        manufacturers = await supplier_crud.list_suppliers(
            business_type=BusinessType.MANUFACTURER
        )
        assert all(s.business_type == BusinessType.MANUFACTURER for s in manufacturers)
    
    async def test_search_suppliers(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试搜索供应商"""
        # 搜索名称
        results = await supplier_crud.search_suppliers("Test")
        assert len(results) > 0
        assert any(s.id == sample_supplier.id for s in results)
        
        # 搜索产品类别
        results = await supplier_crud.search_suppliers("Electronics")
        assert len(results) > 0
    
    async def test_update_supplier(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试更新供应商"""
        await asyncio.sleep(0.1)  # 等待 100ms 确保时间戳变化
        updated = await supplier_crud.update_supplier(
            sample_supplier.id,
            annual_revenue=15000000.0,
            employee_count=600
        )
        
        assert updated is not None
        assert updated.annual_revenue == 15000000.0
        assert updated.employee_count == 600
        assert updated.updated_at >= sample_supplier.updated_at
    
    async def test_delete_supplier(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试删除供应商（软删除）"""
        success = await supplier_crud.delete_supplier(sample_supplier.id)
        assert success is True
        
        # 验证软删除：状态改为INACTIVE
        supplier = await supplier_crud.get_supplier(sample_supplier.id)
        assert supplier is not None
        assert supplier.status == SupplierStatus.INACTIVE
    
    async def test_blacklist_supplier(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试将供应商拉黑"""
        blacklisted = await supplier_crud.blacklist_supplier(
            sample_supplier.id,
            reason="Quality issues"
        )
        
        assert blacklisted is not None
        assert blacklisted.status == SupplierStatus.BLACKLIST
        assert "BLACKLIST" in blacklisted.notes
        assert "Quality issues" in blacklisted.notes


class TestSupplierContactCRUD:
    """供应商联系人CRUD测试"""
    
    async def test_add_contact(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试添加联系人"""
        contact = await supplier_crud.add_contact(
            supplier_id=sample_supplier.id,
            name="John Doe",
            position="Sales Manager",
            email="john@test.com",
            phone="+86-13800138000",
            is_primary=True
        )
        
        assert contact is not None
        assert contact.name == "John Doe"
        assert contact.email == "john@test.com"
        assert contact.is_primary is True
    
    async def test_add_contact_invalid_supplier(self, supplier_crud: SupplierCRUD):
        """测试为不存在的供应商添加联系人"""
        contact = await supplier_crud.add_contact(
            supplier_id=99999,
            name="Jane Doe"
        )
        assert contact is None
    
    async def test_get_contacts(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试获取供应商联系人列表"""
        # 添加2个联系人
        await supplier_crud.add_contact(
            supplier_id=sample_supplier.id,
            name="Contact 1",
            is_primary=True
        )
        await supplier_crud.add_contact(
            supplier_id=sample_supplier.id,
            name="Contact 2",
            is_primary=False
        )
        
        contacts = await supplier_crud.get_contacts(sample_supplier.id)
        
        assert len(contacts) >= 2
        # 主联系人应该排在前面
        assert contacts[0].is_primary is True
    
    async def test_update_contact(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试更新联系人"""
        # 先创建联系人
        contact = await supplier_crud.add_contact(
            supplier_id=sample_supplier.id,
            name="Old Name",
            email="old@test.com"
        )
        
        # 更新联系人
        updated = await supplier_crud.update_contact(
            contact.id,
            name="New Name",
            email="new@test.com"
        )
        
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.email == "new@test.com"
    
    async def test_delete_contact(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试删除联系人"""
        contact = await supplier_crud.add_contact(
            supplier_id=sample_supplier.id,
            name="To Delete"
        )
        
        success = await supplier_crud.delete_contact(contact.id)
        assert success is True


class TestSupplierCertificateCRUD:
    """供应商证书CRUD测试"""
    
    async def test_add_certificate(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试添加证书"""
        issue_date = datetime.utcnow() - timedelta(days=365)
        expiry_date = datetime.utcnow() + timedelta(days=365)
        
        cert = await supplier_crud.add_certificate(
            supplier_id=sample_supplier.id,
            certificate_type="ISO9001",
            certificate_name="ISO 9001 Quality Management System",
            certificate_number="ISO-123456",
            issue_date=issue_date,
            expiry_date=expiry_date,
            issuing_authority="ISO Certification Body",
            is_verified=True
        )
        
        assert cert is not None
        assert cert.certificate_type == CertificateType.ISO9001
        assert cert.certificate_number == "ISO-123456"
        assert cert.is_verified is True
    
    async def test_get_certificates(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试获取证书列表"""
        # 添加有效证书
        await supplier_crud.add_certificate(
            supplier_id=sample_supplier.id,
            certificate_type="ISO14001",
            certificate_name="ISO 14001 Environmental Management",
            certificate_number="ISO-14001",
            issue_date=datetime.utcnow() - timedelta(days=180),
            expiry_date=datetime.utcnow() + timedelta(days=180)
        )
        
        # 添加过期证书
        await supplier_crud.add_certificate(
            supplier_id=sample_supplier.id,
            certificate_type="OTHER",
            certificate_name="Old Certificate",
            certificate_number="OLD-123",
            issue_date=datetime.utcnow() - timedelta(days=730),
            expiry_date=datetime.utcnow() - timedelta(days=30)
        )
        
        # 获取有效证书
        valid_certs = await supplier_crud.get_certificates(
            sample_supplier.id,
            include_expired=False
        )
        assert len(valid_certs) >= 1
        assert all(cert.expiry_date > datetime.utcnow() for cert in valid_certs)
        
        # 获取全部证书
        all_certs = await supplier_crud.get_certificates(
            sample_supplier.id,
            include_expired=True
        )
        assert len(all_certs) >= 2
    
    async def test_update_certificate(self, supplier_crud: SupplierCRUD, sample_supplier):
        """测试更新证书"""
        cert = await supplier_crud.add_certificate(
            supplier_id=sample_supplier.id,
            certificate_type="CE",
            certificate_name="CE Certification",
            certificate_number="CE-001",
            issue_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=365),
            is_verified=False
        )
        
        updated = await supplier_crud.update_certificate(
            cert.id,
            is_verified=True
        )
        
        assert updated is not None
        assert updated.is_verified is True


class TestSupplierRiskAssessmentCRUD:
    """供应商风险评估CRUD测试"""
    
    async def test_create_risk_assessment(
        self, 
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试创建风险评估"""
        assessment = await supplier_crud.create_risk_assessment(
            supplier_id=sample_supplier.id,
            compliance_score=85.0,
            financial_score=80.0,
            delivery_score=90.0,
            quality_score=88.0,
            communication_score=92.0
        )
        
        assert assessment is not None
        assert assessment.compliance_score == 85.0
        assert assessment.overall_score == 87.0  # (85+80+90+88+92)/5
        assert assessment.risk_level == RiskLevel.LOW  # 87 >= 80
        
        # 验证供应商的risk_score已同步更新
        supplier = await supplier_crud.get_supplier(sample_supplier.id)
        assert supplier.risk_score == 87.0
    
    async def test_risk_level_calculation(
        self,
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试风险等级自动计算"""
        # HIGH风险 (40-60)
        high_risk = await supplier_crud.create_risk_assessment(
            supplier_id=sample_supplier.id,
            compliance_score=50.0,
            financial_score=55.0,
            delivery_score=45.0,
            quality_score=48.0,
            communication_score=52.0
        )
        assert high_risk.risk_level == RiskLevel.HIGH
        
        # CRITICAL风险 (<40)
        supplier2 = await supplier_crud.create_supplier(
            name="Supplier 2",
            country="Test",
            product_category="Test"
        )
        critical_risk = await supplier_crud.create_risk_assessment(
            supplier_id=supplier2.id,
            compliance_score=30.0,
            financial_score=25.0,
            delivery_score=35.0,
            quality_score=28.0,
            communication_score=32.0
        )
        assert critical_risk.risk_level == RiskLevel.CRITICAL
    
    async def test_get_latest_risk_assessment(
        self,
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试获取最新风险评估"""
        # 创建2次评估
        await supplier_crud.create_risk_assessment(
            supplier_id=sample_supplier.id,
            compliance_score=70.0,
            financial_score=70.0,
            delivery_score=70.0,
            quality_score=70.0,
            communication_score=70.0
        )
        
        await supplier_crud.create_risk_assessment(
            supplier_id=sample_supplier.id,
            compliance_score=85.0,
            financial_score=85.0,
            delivery_score=85.0,
            quality_score=85.0,
            communication_score=85.0
        )
        
        latest = await supplier_crud.get_latest_risk_assessment(sample_supplier.id)
        
        assert latest is not None
        assert latest.overall_score == 85.0
    
    async def test_get_risk_assessment_history(
        self,
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试获取风险评估历史"""
        # 创建3次评估
        for i in range(3):
            await supplier_crud.create_risk_assessment(
                supplier_id=sample_supplier.id,
                compliance_score=70.0 + i * 5,
                financial_score=70.0 + i * 5,
                delivery_score=70.0 + i * 5,
                quality_score=70.0 + i * 5,
                communication_score=70.0 + i * 5
            )
        
        history = await supplier_crud.get_risk_assessment_history(
            sample_supplier.id,
            limit=5
        )
        
        assert len(history) == 3
        # 验证按时间倒序
        assert history[0].created_at >= history[1].created_at


class TestSupplierStatistics:
    """供应商统计分析测试"""
    
    async def test_get_supplier_count(
        self,
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试获取供应商统计"""
        # 创建不同状态的供应商
        await supplier_crud.create_supplier(
            name="Pending Supplier",
            country="US",
            product_category="Test",
            status=SupplierStatus.PENDING
        )
        
        stats = await supplier_crud.get_supplier_count()
        
        assert 'total' in stats
        assert stats['total'] >= 2
        assert SupplierStatus.ACTIVE.value in stats
        assert SupplierStatus.PENDING.value in stats
    
    async def test_get_suppliers_by_country(
        self,
        supplier_crud: SupplierCRUD,
        sample_supplier
    ):
        """测试按国家统计"""
        # 创建不同国家的供应商
        await supplier_crud.create_supplier(
            name="US Supplier",
            country="USA",
            product_category="Test",
            status=SupplierStatus.ACTIVE
        )
        
        country_stats = await supplier_crud.get_suppliers_by_country()
        
        assert len(country_stats) > 0
        assert "China" in country_stats or "USA" in country_stats
    
    async def test_get_high_risk_suppliers(
        self,
        supplier_crud: SupplierCRUD
    ):
        """测试获取高风险供应商"""
        # 创建高风险供应商
        high_risk_supplier = await supplier_crud.create_supplier(
            name="High Risk Supplier",
            country="Test",
            product_category="Test",
            status=SupplierStatus.ACTIVE,
            risk_score=45.0
        )
        
        high_risk_list = await supplier_crud.get_high_risk_suppliers(limit=10)
        
        # 应该包含我们创建的高风险供应商
        assert any(s.id == high_risk_supplier.id for s in high_risk_list)
        # 所有供应商的risk_score应该<60
        assert all(s.risk_score < 60 for s in high_risk_list if s.risk_score is not None)
