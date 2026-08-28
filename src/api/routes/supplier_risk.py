"""
供应商风险评估 API
Module 48.4 - Supplier Risk Assessment API
 
提供供应商风险评估、历史查询、高风险预警等功能
"""

import json
from datetime import UTC, datetime
from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.models import RiskLevel
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# ==================== Pydantic Schemas ====================


class RiskAssessmentTriggerRequest(BaseModel):
    """触发风险评估请求"""

    assessor: str = Field(default="AI System", description="评估者")


class RiskFactorResponse(BaseModel):
    """风险因素响应"""

    factor_type: str
    weight: float
    description: str


class RiskAssessmentResponse(BaseModel):
    """风险评估响应"""

    id: int
    supplier_id: int
    risk_level: str
    risk_score: float
    risk_factors: dict
    assessment_date: str
    assessor: str
    recommendations: List[str]
    is_active: bool

    model_config = {"from_attributes": True}


class HighRiskSupplierResponse(BaseModel):
    """高风险供应商响应"""

    supplier_id: int
    supplier_name: str
    risk_level: str
    risk_score: float
    assessment_date: str
    recommendations: List[str]


class RiskDistributionResponse(BaseModel):
    """风险分布响应"""

    very_low: int = Field(..., description="极低风险供应商数量")
    low: int = Field(..., description="低风险供应商数量")
    medium: int = Field(..., description="中风险供应商数量")
    high: int = Field(..., description="高风险供应商数量")
    total: int = Field(..., description="总供应商数量")


# ==================== API Endpoints ====================


@router.post("/{supplier_id}/assess-risk", response_model=RiskAssessmentResponse)
async def trigger_risk_assessment(
    supplier_id: int,
    request: RiskAssessmentTriggerRequest = RiskAssessmentTriggerRequest(),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """
    触发供应商风险评估

    权限: supplier:update
    """
    agent = SupplierRiskAgent(session)

    try:
        assessment = await agent.assess_risk(
            supplier_id=supplier_id,
            assessor=request.assessor or current_user.username,
            assessor_id=getattr(current_user, 'id', None),
        )

        # SupplierRiskAgent returns a normalized dict contract in the repository.
        # Preserve that contract and make the route response shape compatible.
        return RiskAssessmentResponse(
            id=assessment.get("assessment_id"),
            supplier_id=assessment.get("supplier_id", supplier_id),
            risk_level=assessment.get("risk_level", "MEDIUM"),
            risk_score=assessment.get("risk_score", assessment.get("overall_score", 50.0)),
            risk_factors=assessment.get("risk_factors", {}),
            assessment_date=datetime.now(UTC).isoformat(),
            assessor=request.assessor or current_user.username,
            recommendations=assessment.get("recommendations", []),
            is_active=True,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("risk_assessment_failed", supplier_id=supplier_id, error=str(e))
        raise HTTPException(status_code=500, detail="风险评估失败")


@router.get("/{supplier_id}/risk-history", response_model=List[RiskAssessmentResponse])
async def get_risk_history(
    supplier_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    获取供应商风险评估历史
    
    权限: supplier:read
    """
    agent = SupplierRiskAgent(session)

    history = await agent.get_risk_history(supplier_id=supplier_id, limit=limit)

    def _risk_factors_from_model(assessment):
        return {
            "strengths": json.loads(assessment.strengths or "[]"),
            "weaknesses": json.loads(assessment.weaknesses or "[]"),
            "opportunities": json.loads(assessment.opportunities or "[]"),
            "threats": json.loads(assessment.threats or "[]"),
        }

    def _recommendations_from_model(assessment):
        try:
            return json.loads(assessment.recommendations or "[]")
        except Exception:
            return []

    return [
        RiskAssessmentResponse(
            id=assessment.id,
            supplier_id=assessment.supplier_id,
            risk_level=assessment.risk_level.name,
            risk_score=assessment.overall_score,
            risk_factors=_risk_factors_from_model(assessment),
            assessment_date=assessment.assessment_date.isoformat(),
            assessor=current_user.username,
            recommendations=_recommendations_from_model(assessment),
            is_active=True,
        )
        for assessment in history
    ]


@router.get("/high-risk", response_model=List[HighRiskSupplierResponse])
async def list_high_risk_suppliers(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    获取所有高风险供应商列表

    权限: supplier:read
    """
    agent = SupplierRiskAgent(session)

    high_risk_suppliers = await agent.get_high_risk_suppliers()

    return [
        HighRiskSupplierResponse(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            risk_level=assessment.risk_level.name,
            risk_score=assessment.risk_score,
            assessment_date=assessment.assessment_date.isoformat(),
            recommendations=assessment.recommendations,
        )
        for supplier, assessment in high_risk_suppliers
    ]


@router.get("/risk-distribution", response_model=RiskDistributionResponse)
async def get_risk_distribution(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    获取供应商风险等级分布统计

    权限: supplier:read
    """
    agent = SupplierRiskAgent(session)

    distribution = await agent.get_risk_distribution()

    total = sum(distribution.values())

    return RiskDistributionResponse(
        very_low=distribution.get(RiskLevel.VERY_LOW.value, 0),
        low=distribution.get(RiskLevel.LOW.value, 0),
        medium=distribution.get(RiskLevel.MEDIUM.value, 0),
        high=distribution.get(RiskLevel.HIGH.value, 0),
        total=total,
    )
