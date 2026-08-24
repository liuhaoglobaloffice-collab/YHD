"""
供应商风险评估 AI Agent 单元测试
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.business.supplier.risk_agent import SupplierRiskAgent, RiskAssessmentError
from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import (
    Supplier,
    SupplierStatus,
    BusinessType,
    RiskLevel,
    CertificateType,
    SupplierRiskAssessment,
)


@pytest.fixture
async def risk_agent(async_session: AsyncSession):
    """创建风险评估 Agent"""
    return SupplierRiskAgent(async_session)


@pytest.fixture
async def sample_supplier_with_data(async_session: AsyncSession):
    """创建带完整数据的供应商"""
    crud = SupplierCRUD(async_session)
    
    # 创建供应商
    supplier = await crud.create_supplier(
        name="Test Supplier Ltd.",
        country="China",
        city="Shenzhen",
        business_type=BusinessType.MANUFACTURER,
        industry="Electronics",
        product_category="Semiconductors",
        registered_capital=5000000.0,
        employee_count=500,
        annual_revenue=10000000.0,
        status=SupplierStatus.ACTIVE,
    )
    
    # 添加联系人
    await crud.add_contact(
        supplier_id=supplier.id,
        name="John Manager",
        position="General Manager",
        email="john@test.com",
        phone="+86-13800138000",
        is_primary=True,
    )
    
    # 添加证书
    await crud.add_certificate(
        supplier_id=supplier.id,
        certificate_type=CertificateType.ISO9001,
        certificate_name="ISO 9001:2015",
        certificate_number="ISO-9001-2024",
        issue_date=datetime.utcnow() - timedelta(days=365),
        expiry_date=datetime.utcnow() + timedelta(days=365),
        is_verified=True,
    )
    
    return supplier


class TestSupplierRiskAgent:
    """供应商风险评估 Agent 测试"""
    
    async def test_assess_risk_success(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试成功评估风险"""
        result = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id,
            save_to_db=True
        )
        
        assert result is not None
        assert "overall_score" in result
        assert "risk_level" in result
        assert "assessment_id" in result
        
        # 验证评分范围
        assert 0 <= result["overall_score"] <= 100
        assert result["risk_level"] in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL
        ]
    
    async def test_assess_risk_invalid_supplier(self, risk_agent: SupplierRiskAgent):
        """测试评估不存在的供应商"""
        with pytest.raises(RiskAssessmentError) as exc_info:
            await risk_agent.assess_risk(supplier_id=99999)
        
        assert "not found" in str(exc_info.value).lower()
    
    async def test_assess_risk_saves_to_database(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试评估结果保存到数据库"""
        result = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id,
            save_to_db=True
        )
        
        # 验证数据库中有记录
        assessment = await risk_agent.get_latest_assessment(
            sample_supplier_with_data.id
        )
        
        assert assessment is not None
        assert assessment.id == result["assessment_id"]
        assert assessment.supplier_id == sample_supplier_with_data.id
        assert assessment.overall_score == result["overall_score"]
    
    async def test_risk_score_range_validation(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试风险评分范围验证"""
        result = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id
        )
        
        # 验证所有评分在 0-100 范围
        assert 0 <= result["compliance_score"] <= 100
        assert 0 <= result["financial_score"] <= 100
        assert 0 <= result["delivery_score"] <= 100
        assert 0 <= result["quality_score"] <= 100
        assert 0 <= result["communication_score"] <= 100
        assert 0 <= result["overall_score"] <= 100
    
    async def test_risk_level_mapping(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试风险等级映射"""
        result = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id
        )
        
        score = result["overall_score"]
        level = result["risk_level"]
        
        # 验证评分与等级匹配
        if 81 <= score <= 100:
            assert level == RiskLevel.LOW
        elif 61 <= score < 81:
            assert level == RiskLevel.MEDIUM
        elif 41 <= score < 61:
            assert level == RiskLevel.HIGH
        elif 0 <= score < 41:
            assert level == RiskLevel.CRITICAL
    
    async def test_swot_analysis_extraction(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试 SWOT 分析提取"""
        result = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id
        )
        
        assert "strengths" in result
        assert "weaknesses" in result
        assert "opportunities" in result
        assert "threats" in result
        
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)
        assert isinstance(result["opportunities"], list)
        assert isinstance(result["threats"], list)
    
    async def test_assess_risk_with_no_certificates(
        self,
        risk_agent: SupplierRiskAgent,
        async_session: AsyncSession
    ):
        """测试评估没有证书的供应商"""
        crud = SupplierCRUD(async_session)
        
        # 创建无证书供应商
        supplier = await crud.create_supplier(
            name="No Cert Supplier",
            country="China",
            product_category="Electronics",
            business_type=BusinessType.TRADING,
            status=SupplierStatus.ACTIVE,
        )
        
        # 不应抛出异常
        result = await risk_agent.assess_risk(supplier_id=supplier.id)
        
        assert result is not None
        # 合规评分可能较低
        assert result["compliance_score"] >= 0
    
    async def test_assess_risk_with_no_contacts(
        self,
        risk_agent: SupplierRiskAgent,
        async_session: AsyncSession
    ):
        """测试评估没有联系人的供应商"""
        crud = SupplierCRUD(async_session)
        
        # 创建无联系人供应商
        supplier = await crud.create_supplier(
            name="No Contact Supplier",
            country="USA",
            product_category="Machinery",
            business_type=BusinessType.MANUFACTURER,
            status=SupplierStatus.ACTIVE,
        )
        
        # 不应抛出异常
        result = await risk_agent.assess_risk(supplier_id=supplier.id)
        
        assert result is not None
        # 沟通评分可能较低
        assert result["communication_score"] >= 0
    
    async def test_risk_assessment_history(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier
    ):
        """测试风险评估历史记录"""
        # 第一次评估
        result1 = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id,
            save_to_db=True
        )
        
        await asyncio.sleep(0.1)  # 确保时间戳不同
        
        # 第二次评估
        result2 = await risk_agent.assess_risk(
            supplier_id=sample_supplier_with_data.id,
            save_to_db=True
        )
        
        # 两次评估应该有不同的 ID
        assert result1["assessment_id"] != result2["assessment_id"]
        
        # 获取最新评估
        latest = await risk_agent.get_latest_assessment(
            sample_supplier_with_data.id
        )
        assert latest.id == result2["assessment_id"]
    
    async def test_calculate_risk_trend_improving(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier,
        async_session: AsyncSession
    ):
        """测试风险趋势计算 - 改善"""
        from src.business.supplier.models import SupplierRiskAssessment
        
        # 创建历史评估：从低分到高分
        for i, score in enumerate([40, 55, 70, 85]):
            assessment = SupplierRiskAssessment(
                supplier_id=sample_supplier_with_data.id,
                overall_score=float(score),
                risk_level=RiskLevel.MEDIUM,
                compliance_score=float(score),
                financial_score=float(score),
                delivery_score=float(score),
                quality_score=float(score),
                communication_score=float(score),
                strengths='["Good"]',
                weaknesses='["Bad"]',
                opportunities='["Opportunity"]',
                threats='["Threat"]',
                created_at=datetime.utcnow() - timedelta(days=30*(3-i)),
                updated_at=datetime.utcnow(),
            )
            async_session.add(assessment)
        
        await async_session.commit()
        
        trend = await risk_agent.calculate_risk_trend(
            sample_supplier_with_data.id,
            lookback_days=90
        )
        
        assert trend == "IMPROVING"
    
    async def test_calculate_risk_trend_declining(
        self,
        risk_agent: SupplierRiskAgent,
        sample_supplier_with_data: Supplier,
        async_session: AsyncSession
    ):
        """测试风险趋势计算 - 恶化"""
        from src.business.supplier.models import SupplierRiskAssessment
        
        # 创建历史评估：从高分到低分
        for i, score in enumerate([85, 70, 55, 40]):
            assessment = SupplierRiskAssessment(
                supplier_id=sample_supplier_with_data.id,
                overall_score=float(score),
                risk_level=RiskLevel.MEDIUM,
                compliance_score=float(score),
                financial_score=float(score),
                delivery_score=float(score),
                quality_score=float(score),
                communication_score=float(score),
                strengths='["Good"]',
                weaknesses='["Bad"]',
                opportunities='["Opportunity"]',
                threats='["Threat"]',
                created_at=datetime.utcnow() - timedelta(days=30*(3-i)),
                updated_at=datetime.utcnow(),
            )
            async_session.add(assessment)
        
        await async_session.commit()
        
        trend = await risk_agent.calculate_risk_trend(
            sample_supplier_with_data.id,
            lookback_days=90
        )
        
        assert trend == "DECLINING"
    
    async def test_get_default_assessment(self, risk_agent: SupplierRiskAgent):
        """测试获取默认评估"""
        default = risk_agent._get_default_assessment()
        
        assert default["overall_score"] == 50.0
        assert default["risk_level"] == RiskLevel.MEDIUM
        assert len(default["strengths"]) > 0
        assert len(default["weaknesses"]) > 0
    
    async def test_parse_ai_response_valid_json(self, risk_agent: SupplierRiskAgent):
        """测试解析有效的 AI JSON 响应"""
        response = """
        Here is the assessment:
        {
          "compliance_score": 75.0,
          "financial_score": 80.0,
          "delivery_score": 70.0,
          "quality_score": 85.0,
          "communication_score": 90.0,
          "overall_score": 80.0,
          "risk_level": "MEDIUM",
          "strengths": ["Good quality", "Fast response"],
          "weaknesses": ["High price"],
          "opportunities": ["Market expansion"],
          "threats": ["Competition"]
        }
        """
        
        result = risk_agent._parse_ai_response(response)
        
        assert result["overall_score"] == 80.0
        assert result["risk_level"] == RiskLevel.MEDIUM
        assert len(result["strengths"]) == 2
    
    async def test_parse_ai_response_invalid_json(self, risk_agent: SupplierRiskAgent):
        """测试解析无效的 AI 响应"""
        response = "This is not a valid JSON response"
        
        result = risk_agent._parse_ai_response(response)
        
        # 应返回默认评估
        assert result["overall_score"] == 50.0
        assert result["risk_level"] == RiskLevel.MEDIUM

    async def test_save_assessment_knowledge(self, risk_agent: SupplierRiskAgent, sample_supplier_with_data: Supplier):
        """测试保存风险评估到知识库"""
        # 评估风险并保存到数据库
        result = await risk_agent.assess_risk(sample_supplier_with_data.id, save_to_db=True)
        assessment_id = result["assessment_id"]
        
        # 查询 assessment 对象
        stmt = select(SupplierRiskAssessment).where(SupplierRiskAssessment.id == assessment_id)
        db_result = await risk_agent.db.execute(stmt)
        assessment = db_result.scalar_one()
        
        # 保存到知识库
        knowledge_id = await risk_agent.save_assessment_knowledge(sample_supplier_with_data.id, assessment)
        
        # 验证返回的知识数据
        assert isinstance(knowledge_id, dict)
        assert knowledge_id["supplier_id"] == sample_supplier_with_data.id
        assert knowledge_id["assessment_id"] == assessment_id
        assert "risk_level" in knowledge_id
        assert "overall_score" in knowledge_id

    async def test_retrieve_similar_assessments(self, risk_agent: SupplierRiskAgent, sample_supplier_with_data: Supplier):
        """测试检索相似的风险评估"""
        
        # 先创建评估
        result = await risk_agent.assess_risk(sample_supplier_with_data.id, save_to_db=True)
        assessment_id = result["assessment_id"]
        
        # 查询 assessment 对象
        stmt = select(SupplierRiskAssessment).where(SupplierRiskAssessment.id == assessment_id)
        db_result = await risk_agent.db.execute(stmt)
        assessment = db_result.scalar_one()
        
        # 保存到知识库
        await risk_agent.save_assessment_knowledge(sample_supplier_with_data.id, assessment)
        
        # 检索相似评估
        similar = await risk_agent.retrieve_similar_assessments(
            supplier_id=sample_supplier_with_data.id,
            limit=5
        )
        
        assert len(similar) >= 1
        # retrieve_similar_assessments 返回 ORM 对象，不是 dict
        assert similar[0].supplier_id == sample_supplier_with_data.id
        assert similar[0].risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert hasattr(similar[0], "created_at")
