"""
供应商风险评估 AI Agent

使用 AI 分析供应商的多维度风险，生成结构化评估报告。
"""

import json
import os
from datetime import UTC, datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

# from src.ai.core import get_ai_brain  # REMOVED: No such module
from src.business.supplier.crud import SupplierCRUD
from src.providers.registry import get_provider
from src.business.supplier.models import (
    Supplier,
    SupplierRiskAssessment,
    RiskLevel,
)
from src.core.errors import LiuHaoError

logger = structlog.get_logger(__name__)


class RiskAssessmentError(LiuHaoError):
    """风险评估错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RISK_ASSESSMENT_ERROR",
            message=message,
            details=details or {}
        )


class SupplierRiskAgent:
    """
    供应商风险评估 AI Agent
    
    使用 AI 分析供应商的完整信息，从多个维度评估风险：
    - 合规风险 (compliance)
    - 财务风险 (financial)
    - 履约风险 (delivery)
    - 质量风险 (quality)
    - 沟通风险 (communication)
    """
    
    def __init__(self, db: AsyncSession, provider=None):
        """
        初始化风险评估 Agent
        
        Args:
            db: 数据库会话
            provider: optional provider adapter, default to mock registry
        """
        self.db = db
        self.crud = SupplierCRUD(db)
        self.provider = provider or get_provider("mock")
        # self.ai_brain = get_ai_brain()  # MOCK VERSION  # 使用 AI Brain 进行分析
        
    async def assess_risk(
        self,
        supplier_id: int,
        save_to_db: bool = True,
        assessor: Optional[str] = None,
        assessor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        评估供应商风险
        
        Args:
            supplier_id: 供应商 ID
            save_to_db: 是否保存评估结果到数据库
            
        Returns:
            风险评估结果字典
            
        Raises:
            RiskAssessmentError: 评估失败时抛出
        """
        logger.info("starting_risk_assessment", supplier_id=supplier_id)
        
        # 1. 获取供应商完整信息
        supplier_data = await self._gather_supplier_data(supplier_id)
        if not supplier_data:
            raise RiskAssessmentError(
                f"Supplier {supplier_id} not found",
                {"supplier_id": supplier_id}
            )
        
        # 2. 构建 AI Prompt
        prompt = self._build_assessment_prompt(supplier_data)
        
        # 3. 调用 AI 分析
        try:
            ai_response = await self._call_ai_analysis(prompt)
            parsed = self._parse_ai_response(ai_response)
        except Exception as e:
            logger.error("ai_analysis_failed", error=str(e))
            # 返回默认评估
            parsed = self._get_default_assessment()

        # Normalize result for external contract
        normalized = self._normalize_risk_result(supplier_id, parsed, parsed.get("overall_score"))

        # 4. 保存到数据库 (save parsed/raw scores)
        if save_to_db:
            assessment = await self._save_assessment(
                supplier_id,
                parsed,
                assessor=assessor,
                assessor_id=assessor_id,
            )
            normalized["assessment_id"] = assessment.id
            # ensure risk_level uses stored enum name
            normalized["risk_level"] = assessment.risk_level.name
            normalized["overall_score"] = assessment.overall_score
            normalized["risk_score"] = assessment.overall_score

        logger.info(
            "risk_assessment_completed",
            supplier_id=supplier_id,
            risk_level=normalized.get("risk_level"),
            overall_score=normalized.get("overall_score")
        )

        return normalized
    
    async def _gather_supplier_data(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        """
        收集供应商完整信息
        
        Args:
            supplier_id: 供应商 ID
            
        Returns:
            供应商数据字典，如果不存在返回 None
        """
        # 获取供应商基本信息
        supplier = await self.crud.get_supplier(supplier_id)
        if not supplier:
            return None
        
        # 获取联系人
        contacts = await self.crud.get_contacts(supplier_id)
        
        # 获取证书
        certificates = await self.crud.get_certificates(supplier_id)
        
        # 获取历史风险评估
        stmt = select(SupplierRiskAssessment).where(
            SupplierRiskAssessment.supplier_id == supplier_id
        ).order_by(SupplierRiskAssessment.created_at.desc()).limit(3)
        result = await self.db.execute(stmt)
        history = result.scalars().all()
        
        return {
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "country": supplier.country,
                "city": supplier.city,
                "business_type": supplier.business_type.value if supplier.business_type else None,
                "industry": supplier.industry,
                "product_category": supplier.product_category,
                "established_date": supplier.established_date.isoformat() if supplier.established_date else None,
                "registered_capital": supplier.registered_capital,
                "employee_count": supplier.employee_count,
                "annual_revenue": supplier.annual_revenue,
                "website": supplier.website,
                "status": supplier.status.value,
            },
            "contacts": [
                {
                    "name": c.name,
                    "position": c.position,
                    "department": c.department,
                    "email": c.email,
                    "phone": c.phone,
                    "is_primary": c.is_primary,
                }
                for c in contacts
            ],
            "certificates": [
                {
                    "type": c.certificate_type.value if hasattr(c.certificate_type, 'value') else str(c.certificate_type),
                    "name": c.certificate_name,
                    "number": c.certificate_number,
                    "issuing_authority": c.issuing_authority,
                    "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                    "is_verified": c.is_verified,
                }
                for c in certificates
            ],
            "history": [
                {
                    "overall_score": h.overall_score,
                    "risk_level": h.risk_level.value if hasattr(h.risk_level, 'value') else str(h.risk_level),
                    "assessed_at": h.created_at.isoformat(),
                }
                for h in history
            ]
        }
    
    def _build_assessment_prompt(self, supplier_data: Dict[str, Any]) -> str:
        """
        构建 AI 分析 Prompt
        
        Args:
            supplier_data: 供应商数据
            
        Returns:
            格式化的 Prompt 字符串
        """
        supplier = supplier_data["supplier"]
        contacts = supplier_data["contacts"]
        certificates = supplier_data["certificates"]
        history = supplier_data["history"]
        
        prompt = f"""You are a professional supplier risk assessment expert. Analyze the following supplier information and provide a comprehensive risk assessment.

**Supplier Information:**
- Name: {supplier['name']}
- Country: {supplier['country']}
- Business Type: {supplier['business_type']}
- Industry: {supplier['industry']}
- Product Category: {supplier['product_category']}
- Established: {supplier['established_date']}
- Registered Capital: ${supplier['registered_capital']}
- Employees: {supplier['employee_count']}
- Annual Revenue: ${supplier['annual_revenue']}
- Status: {supplier['status']}

**Contacts ({len(contacts)}):**
{json.dumps(contacts, indent=2, ensure_ascii=False)}

**Certificates ({len(certificates)}):**
{json.dumps(certificates, indent=2, ensure_ascii=False)}

**Historical Assessments ({len(history)}):**
{json.dumps(history, indent=2, ensure_ascii=False)}

**Assessment Requirements:**
Please evaluate the supplier across 5 dimensions (score 0-100, higher is better):
1. Compliance Score: Legal, certifications, regulations
2. Financial Score: Capital, revenue, financial stability
3. Delivery Score: On-time delivery capability, contract execution
4. Quality Score: Product quality, customer complaints
5. Communication Score: Response speed, service attitude

Also provide:
- Overall Score (0-100): Weighted average of all dimensions
- Risk Level: LOW (81-100), MEDIUM (61-80), HIGH (41-60), CRITICAL (0-40)
- SWOT Analysis: Strengths, Weaknesses, Opportunities, Threats (3-5 points each)

**Output Format (JSON):**
{{
  "compliance_score": <float>,
  "financial_score": <float>,
  "delivery_score": <float>,
  "quality_score": <float>,
  "communication_score": <float>,
  "overall_score": <float>,
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
  "opportunities": ["<opportunity 1>", "<opportunity 2>", ...],
  "threats": ["<threat 1>", "<threat 2>", ...]
}}

Provide ONLY the JSON output, no additional text."""
        
        return prompt
    
    async def _call_ai_analysis(self, prompt: str) -> str:
        """
        调用 AI 进行分析

        优先使用 Provider Gateway（统一 LLM 调用链，支持 OpenAI / Ollama 真实模型）；
        若 Gateway 未就绪或未配置真实 Provider，则回退到旧版 provider adapter；
        最后回退到内置 mock 兜底 JSON。

        Args:
            prompt: AI Prompt

        Returns:
            AI 响应文本.
        """
        # 1) 尝试 Provider Gateway 统一链路（LLM_PROVIDER != mock 时启用真实 LLM）
        try:
            provider_str = os.getenv("LLM_PROVIDER", "mock").lower().strip()
            if provider_str in ("openai", "ollama"):
                from src.ai.gateway import get_gateway

                gateway = get_gateway()
                # 任选一个已注册 provider + model（真实 Provider 已在启动时注册）
                providers = gateway.list_providers()
                if providers:
                    ptype = providers[0]
                    models = gateway.list_models(ptype)
                    model_id = models[0].model_id if models else ptype.value
                    response = await gateway.complete(
                        provider=ptype,
                        model_id=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        trace_id=uuid4(),
                        temperature=0.2,
                        max_tokens=2048,
                    )
                    if response and response.content:
                        logger.info(
                            "risk_ai_gateway_used", provider=ptype.value, model=model_id
                        )
                        return response.content
        except Exception as e:
            logger.warning("risk_ai_gateway_failed_falling_back", error=str(e))

        # 2) 回退到旧版 provider adapter（默认 mock）
        if hasattr(self, "provider") and self.provider is not None:
            return await self.provider.analyze(prompt)
        return json.dumps({
            "compliance_score": 75.0,
            "financial_score": 80.0,
            "delivery_score": 70.0,
            "quality_score": 85.0,
            "communication_score": 90.0,
            "overall_score": 80.0,
            "risk_level": "MEDIUM",
            "strengths": ["高品质产品", "响应迅速"],
            "weaknesses": ["价格偏高"],
            "opportunities": ["市场扩张机会"],
            "threats": ["市场竞争激烈"]
        }, ensure_ascii=False)
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        解析 AI 响应
        
        Args:
            response: AI 响应文本
            
        Returns:
            解析后的风险数据
        """
        try:
            # 提取 JSON (可能被包裹在其他文本中)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start:end]
            data = json.loads(json_str)
            
            # 验证必需字段
            required_fields = [
                "compliance_score", "financial_score", "delivery_score",
                "quality_score", "communication_score", "overall_score",
                "risk_level", "strengths", "weaknesses", "opportunities", "threats"
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # 映射风险等级
            risk_level_map = {
                "VERY_LOW": RiskLevel.VERY_LOW,
                "LOW": RiskLevel.LOW,
                "MEDIUM": RiskLevel.MEDIUM,
                "HIGH": RiskLevel.HIGH,
                "CRITICAL": RiskLevel.CRITICAL,
            }
            data["risk_level"] = risk_level_map.get(
                data["risk_level"].upper(),
                RiskLevel.MEDIUM
            )
            
            return data
            
        except Exception as e:
            logger.error("ai_response_parsing_failed", error=str(e), response=response)
            return self._get_default_assessment()
    
    def _get_default_assessment(self) -> Dict[str, Any]:
        """
        获取默认评估结果（AI 失败时使用）
        
        Returns:
            默认风险评估数据
        """
        return {
            "compliance_score": 50.0,
            "financial_score": 50.0,
            "delivery_score": 50.0,
            "quality_score": 50.0,
            "communication_score": 50.0,
            "overall_score": 50.0,
            "risk_level": RiskLevel.MEDIUM,
            "strengths": ["待人工评估"],
            "weaknesses": ["待人工评估"],
            "opportunities": ["待人工评估"],
            "threats": ["待人工评估"],
        }
    
    async def _save_assessment(
        self,
        supplier_id: int,
        risk_data: Dict[str, Any],
        assessor: Optional[str] = None,
        assessor_id: Optional[int] = None,
    ) -> SupplierRiskAssessment:
        """
        保存风险评估到数据库
        
        Args:
            supplier_id: 供应商 ID
            risk_data: 风险评估数据
            
        Returns:
            保存的评估记录
        """
        assessment = SupplierRiskAssessment(
            supplier_id=supplier_id,
            compliance_score=risk_data["compliance_score"],
            financial_score=risk_data["financial_score"],
            delivery_score=risk_data["delivery_score"],
            quality_score=risk_data["quality_score"],
            communication_score=risk_data["communication_score"],
            overall_score=risk_data["overall_score"],
            risk_level=risk_data["risk_level"],
            strengths=json.dumps(risk_data["strengths"], ensure_ascii=False),
            weaknesses=json.dumps(risk_data["weaknesses"], ensure_ascii=False),
            opportunities=json.dumps(risk_data["opportunities"], ensure_ascii=False),
            threats=json.dumps(risk_data["threats"], ensure_ascii=False),
            recommendations=json.dumps(risk_data.get("recommendations", []), ensure_ascii=False),
            assessor_id=assessor_id,
            assessment_method="ai" if assessor else "manual",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        
        # 5. 保存到知识库 (Phase 1: 简单存储)
        await self.save_assessment_knowledge(supplier_id, assessment)
        
        logger.info(
            "risk_assessment_saved",
            assessment_id=assessment.id,
            supplier_id=supplier_id
        )
        
        return assessment
    
    def _normalize_risk_result(self, supplier_id: int, parsed: Dict[str, Any], overall_score: Optional[float] = None) -> Dict[str, Any]:
        """
        Normalize parsed AI result into the external contract expected by API and tests.
        Returns a dict with keys: supplier_id, risk_level, risk_score, overall_score, risk_factors, recommendations, assessment_id
        """
        # Ensure risk_level is a RiskLevel enum
        rl = parsed.get("risk_level")
        if isinstance(rl, RiskLevel):
            risk_level_enum = rl
        else:
            try:
                # parsed risk_level may be a string like 'LOW' or 'low'
                risk_level_enum = RiskLevel[rl.upper()]
            except Exception:
                risk_level_enum = RiskLevel.MEDIUM

        overall = overall_score if overall_score is not None else parsed.get("overall_score", 50.0)

        risk_factors = {
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "opportunities": parsed.get("opportunities", []),
            "threats": parsed.get("threats", []),
        }

        return {
            "supplier_id": supplier_id,
            "risk_level": risk_level_enum.name,
            "risk_score": parsed.get("overall_score", overall),
            "overall_score": overall,
            "risk_factors": risk_factors,
            "recommendations": parsed.get("recommendations", []),
            "assessment_id": None,
        }

    async def get_risk_history(
        self,
        supplier_id: int,
        limit: int = 10,
    ) -> List[SupplierRiskAssessment]:
        """
        Return supplier assessment history most-recent-first, keeping the
        agent API contract consistent with the routes and tests.
        """
        stmt = (
            select(SupplierRiskAssessment)
            .where(SupplierRiskAssessment.supplier_id == supplier_id)
            .order_by(desc(SupplierRiskAssessment.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_risk_distribution(self) -> Dict[str, int]:
        """
        Return a latest-per-supplier distribution of assessment risk levels.
        This keeps the supplier-risk agent contract available for API and UI
        consumers without forcing a larger architectural rewrite.
        """
        stmt = (
            select(SupplierRiskAssessment)
            .order_by(desc(SupplierRiskAssessment.created_at))
        )
        result = await self.db.execute(stmt)
        assessments = list(result.scalars().all())

        latest_by_supplier: Dict[int, SupplierRiskAssessment] = {}
        for assessment in assessments:
            supplier_id = assessment.supplier_id
            if supplier_id not in latest_by_supplier:
                latest_by_supplier[supplier_id] = assessment

        distribution = {
            "VERY_LOW": 0,
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0,
        }

        for assessment in latest_by_supplier.values():
            level = assessment.risk_level.name if hasattr(assessment.risk_level, "name") else str(assessment.risk_level)
            level = level.upper()
            if level in distribution:
                distribution[level] += 1

        return distribution

    async def get_high_risk_suppliers(
        self,
        limit: int = 10,
    ) -> List[tuple[Supplier, SupplierRiskAssessment]]:
        """
        Return high-risk suppliers as tuples of (Supplier, latest high-risk assessment)
        deduped by supplier ID and bounded by the requested limit.
        """
        stmt = (
            select(SupplierRiskAssessment)
            .where(
                SupplierRiskAssessment.risk_level.in_([
                    RiskLevel.HIGH,
                    RiskLevel.CRITICAL,
                ])
            )
            .order_by(desc(SupplierRiskAssessment.created_at))
        )
        result = await self.db.execute(stmt)
        assessments = list(result.scalars().all())

        high_suppliers: List[tuple[Supplier, SupplierRiskAssessment]] = []
        seen = set()
        for assessment in assessments:
            supplier_id = assessment.supplier_id
            if supplier_id in seen:
                continue
            supplier = await self.db.get(Supplier, supplier_id)
            if supplier is None:
                continue
            high_suppliers.append((supplier, assessment))
            seen.add(supplier_id)
            if len(high_suppliers) >= limit:
                break

        return high_suppliers

    async def get_latest_assessment(
        self,
        supplier_id: int
    ) -> Optional[SupplierRiskAssessment]:
        """
        获取供应商最新的风险评估
        
        Args:
            supplier_id: 供应商 ID
             
        Returns:
            最新的评估记录，如果不存在返回 None
        """
        stmt = select(SupplierRiskAssessment).where(
            SupplierRiskAssessment.supplier_id == supplier_id
        ).order_by(SupplierRiskAssessment.created_at.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def calculate_risk_trend(
        self,
        supplier_id: int,
        lookback_days: int = 90
    ) -> str:
        """
        计算风险趋势
        
        Args:
            supplier_id: 供应商 ID
            lookback_days: 回溯天数
            
        Returns:
            趋势: "IMPROVING" (改善), "STABLE" (稳定), "DECLINING" (恶化)
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now(UTC) - timedelta(days=lookback_days)
        
        stmt = select(SupplierRiskAssessment).where(
            SupplierRiskAssessment.supplier_id == supplier_id,
            SupplierRiskAssessment.created_at >= cutoff_date
        ).order_by(SupplierRiskAssessment.created_at.asc())
        
        result = await self.db.execute(stmt)
        assessments = result.scalars().all()
        
        if len(assessments) < 2:
            return "STABLE"
        
        # 计算趋势：比较首尾评分
        first_score = assessments[0].overall_score or 50.0
        last_score = assessments[-1].overall_score or 50.0
        
        diff = last_score - first_score
        
        if diff > 5:
            return "IMPROVING"
        elif diff < -5:
            return "DECLINING"
        else:
            return "STABLE"

    async def save_assessment_knowledge(
        self,
        supplier_id: int,
        assessment: SupplierRiskAssessment,
    ) -> Dict[str, Any]:
        """
        将风险评估结果保存到知识库 (Phase 1: 简单 JSON 存储)
        
        未来升级:
        - 向量化内容 (embedding)
        - 存储到 Knowledge Base
        - 支持语义检索
        """
        knowledge_data = {
            "supplier_id": supplier_id,
            "assessment_id": assessment.id,
            "risk_level": assessment.risk_level.name,
            "overall_score": float(assessment.overall_score),
            "created_at": assessment.created_at.isoformat(),
            "summary": f"供应商 {supplier_id} 的风险评估：等级 {assessment.risk_level.name}，评分 {assessment.overall_score}",
            "strengths": assessment.strengths,
            "weaknesses": assessment.weaknesses,
            "opportunities": assessment.opportunities,
            "threats": assessment.threats,
            # TODO: 向量化 summary 并存储 embedding
            # "embedding": await self._get_embedding(knowledge_data["summary"])
        }
        
        logger.info(
            "assessment_knowledge_saved",
            supplier_id=supplier_id,
            assessment_id=assessment.id,
        )
        
        return knowledge_data

    async def retrieve_similar_assessments(
        self,
        supplier_id: int,
        limit: int = 5,
    ) -> List[SupplierRiskAssessment]:
        """
        检索相似的历史风险评估 (Phase 1: 简单历史查询)
        
        未来升级:
        - 基于 embedding 的语义相似度检索
        - 跨供应商的相似案例检索
        """
        stmt = (
            select(SupplierRiskAssessment)
            .where(SupplierRiskAssessment.supplier_id == supplier_id)
            .order_by(SupplierRiskAssessment.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        assessments = result.scalars().all()
        
        logger.info(
            "similar_assessments_retrieved",
            supplier_id=supplier_id,
            count=len(assessments),
        )
        
        return list(assessments)

    # TODO: Phase 2 - 实现向量化功能
    # async def _get_embedding(self, text: str) -> List[float]:
    #     """获取文本向量 (embedding)"""
    #     # 调用 OpenAI text-embedding-3-small
    #     provider = get_provider("openai")
    #     response = await provider.create_embedding(
    #         input=text,
    #         model="text-embedding-3-small"
    #     )
    #     return response.data[0].embedding
