"""
CEO API Routes

Executive dashboard endpoints.
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.dependencies import (
    get_business_task_registry,
    get_current_user,
    get_db_session,
    get_employee_registry,
)
from src.api.dependencies.database import get_db
from src.business.registry import BusinessTaskRegistry
from src.ceo.dashboard import CEODashboard, get_ceo_dashboard
from src.ceo.models import (
    AITeamOverview,
    ApprovalOverview,
    BusinessOverview,
    CEODashboardData,
    SystemOverview,
    TaskOverview,
)
from src.governance.approval import ApprovalService
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.workforce.registry import AIEmployeeRegistry
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.crud import SupplierCRUD
from pydantic import BaseModel, Field
from typing import List, Dict

router = APIRouter(prefix="/ceo", tags=["CEO Dashboard"])


def get_dashboard_service(
    business_registry: BusinessTaskRegistry = Depends(get_business_task_registry),
    employee_registry: AIEmployeeRegistry = Depends(get_employee_registry),
    session: AsyncSession = Depends(get_db_session),
) -> CEODashboard:
    """Dependency: Get CEO dashboard service."""
    # Create service instances for CEO dashboard with database session
    approval_service = ApprovalService(session=session)
    audit_service = AuditService()

    # Create RBAC service with database session
    rbac_service = RBACService(session=session)
    return get_ceo_dashboard(
        business_registry=business_registry,
        employee_registry=employee_registry,
        approval_service=approval_service,
        audit_service=audit_service,
        rbac_service=rbac_service,
    )


@router.get(
    "/dashboard",
    response_model=CEODashboardData,
    summary="Get complete CEO dashboard",
)
async def get_dashboard(
    user: User = Depends(get_current_user),
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range (1-720 hours)"),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get complete CEO dashboard with all metrics.

    Requires SYSTEM_ADMIN permission.

    Time range controls business/task metrics window.
    """
    try:
        return await dashboard.get_dashboard(
            user_id=user.id,
            time_range_hours=time_range_hours,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}",
        )


@router.get(
    "/system",
    response_model=SystemOverview,
    summary="Get system overview",
)
async def get_system(
    user: User = Depends(get_current_user),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get system health and infrastructure metrics.

    Requires SYSTEM_ADMIN permission.
    """
    try:
        return await dashboard.get_system_overview(user_id=user.id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system overview: {str(e)}",
        )


@router.get(
    "/business",
    response_model=BusinessOverview,
    summary="Get business overview",
)
async def get_business(
    user: User = Depends(get_current_user),
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range (1-720 hours)"),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get business operations metrics.

    Requires SYSTEM_ADMIN permission.
    """
    try:
        return await dashboard.get_business_overview(
            user_id=user.id,
            time_range_hours=time_range_hours,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get business overview: {str(e)}",
        )


@router.get(
    "/ai-team",
    response_model=AITeamOverview,
    summary="Get AI team overview",
)
async def get_ai_team(
    user: User = Depends(get_current_user),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get AI workforce metrics and top performers.

    Requires SYSTEM_ADMIN permission.
    """
    try:
        return await dashboard.get_ai_team_overview(user_id=user.id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI team overview: {str(e)}",
        )


@router.get(
    "/tasks",
    response_model=TaskOverview,
    summary="Get task overview",
)
async def get_tasks(
    user: User = Depends(get_current_user),
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range (1-720 hours)"),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get task & workflow execution metrics.

    Requires SYSTEM_ADMIN permission.
    """
    try:
        return await dashboard.get_task_overview(
            user_id=user.id,
            time_range_hours=time_range_hours,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task overview: {str(e)}",
        )


@router.get(
    "/approvals",
    response_model=ApprovalOverview,
    summary="Get approval overview",
)
async def get_approvals(
    user: User = Depends(get_current_user),
    dashboard: CEODashboard = Depends(get_dashboard_service),
):
    """
    Get approval & governance metrics.

    Requires SYSTEM_ADMIN permission.
    """
    try:
        return await dashboard.get_approval_overview(user_id=user.id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval overview: {str(e)}",
        )


# ==================== Supplier Dashboard ====================  


class SupplierStatsResponse(BaseModel):
    """供应商统计数据"""

    total: int = Field(..., description="总供应商数")
    active: int = Field(..., description="活跃供应商数")
    pending: int = Field(..., description="待审核供应商数")
    blacklisted: int = Field(..., description="黑名单供应商数")
    high_risk: int = Field(..., description="高风险供应商数")


class RiskDistributionResponse(BaseModel):
    """风险分布数据"""

    very_low: int
    low: int
    medium: int
    high: int
    total: int


@router.get("/suppliers/stats", response_model=SupplierStatsResponse)
async def get_supplier_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取供应商统计数据"""
    crud = SupplierCRUD(session)
    agent = SupplierRiskAgent(session)

    # 获取所有供应商
    all_suppliers = await crud.list_suppliers()

    # 统计各状态数量
    from src.business.supplier.models import SupplierStatus
    
    active = sum(1 for s in all_suppliers if s.status == SupplierStatus.ACTIVE)
    pending = sum(1 for s in all_suppliers if s.status == SupplierStatus.PENDING)
    blacklisted = sum(1 for s in all_suppliers if s.status == SupplierStatus.BLACKLISTED)

    # 获取高风险供应商数
    high_risk_suppliers = await agent.get_high_risk_suppliers()

    return SupplierStatsResponse(
        total=len(all_suppliers),
        active=active,
        pending=pending,
        blacklisted=blacklisted,
        high_risk=len(high_risk_suppliers),
    )


@router.get("/suppliers/risk-distribution", response_model=RiskDistributionResponse)
async def get_supplier_risk_distribution(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取供应商风险分布"""
    agent = SupplierRiskAgent(session)
    distribution = await agent.get_risk_distribution()

    from src.business.supplier.models import RiskLevel
    
    total = sum(distribution.values())

    return RiskDistributionResponse(
        very_low=distribution.get(RiskLevel.VERY_LOW.value, 0),
        low=distribution.get(RiskLevel.LOW.value, 0),
        medium=distribution.get(RiskLevel.MEDIUM.value, 0),
        high=distribution.get(RiskLevel.HIGH.value, 0),
        total=total,
    )
