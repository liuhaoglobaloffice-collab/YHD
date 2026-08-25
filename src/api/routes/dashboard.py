"""
Dashboard API Routes
CEO 仪表板数据接口
"""

from typing import Dict, List
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.business.supplier.models import Supplier, SupplierStatus, BusinessType
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    获取 CEO 仪表板核心统计数据
    """
    logger.info("fetching_dashboard_stats", user_id=current_user.id)
    
    # 供应商总数
    total_suppliers_result = await db.execute(
        select(func.count(Supplier.id))
    )
    total_suppliers = total_suppliers_result.scalar() or 0
    
    # 活跃供应商数
    active_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.status == SupplierStatus.ACTIVE
        )
    )
    active_suppliers = active_suppliers_result.scalar() or 0
    
    # 本月新增供应商
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.created_at >= thirty_days_ago
        )
    )
    new_suppliers = new_suppliers_result.scalar() or 0
    
    # 高风险供应商数
    high_risk_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.risk_level.in_(["high", "critical"])
        )
    )
    high_risk_suppliers = high_risk_result.scalar() or 0
    
    # 按业务类型统计
    business_type_stats = []
    for biz_type in BusinessType:
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.business_type == biz_type
            )
        )
        count = count_result.scalar() or 0
        business_type_stats.append({
            "type": biz_type.value,
            "count": count
        })
    
    # 按风险等级统计
    risk_distribution = {}
    for risk_level in ["low", "medium", "high", "critical"]:
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.risk_level == risk_level
            )
        )
        count = count_result.scalar() or 0
        risk_distribution[risk_level] = count
    
    return {
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "new_suppliers_this_month": new_suppliers,
        "high_risk_suppliers": high_risk_suppliers,
        "business_type_distribution": business_type_stats,
        "risk_distribution": risk_distribution,
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/trends")
async def get_dashboard_trends(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    获取趋势数据（过去 N 天）
    """
    logger.info("fetching_dashboard_trends", user_id=current_user.id, days=days)
    
    # 计算日期范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 每日新增供应商趋势
    daily_new_suppliers = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.created_at >= day_start,
                Supplier.created_at < day_end
            )
        )
        count = count_result.scalar() or 0
        daily_new_suppliers.append({
            "date": day_start.date().isoformat(),
            "count": count
        })
    
    return {
        "period": {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "days": days
        },
        "daily_new_suppliers": daily_new_suppliers,
    }


@router.get("/top-suppliers")
async def get_top_suppliers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取优质供应商列表（低风险 + 活跃）
    """
    logger.info("fetching_top_suppliers", user_id=current_user.id, limit=limit)
    
    result = await db.execute(
        select(Supplier)
        .where(
            Supplier.status == SupplierStatus.ACTIVE,
            Supplier.risk_level == "low"
        )
        .order_by(Supplier.created_at.desc())
        .limit(limit)
    )
    suppliers = result.scalars().all()
    
    return [
        {
            "id": str(supplier.id),
            "name": supplier.name,
            "business_type": supplier.business_type.value,
            "risk_level": supplier.risk_level,
            "status": supplier.status.value,
            "contact_email": supplier.contact_email,
        }
        for supplier in suppliers
    ]


@router.get("/alerts")
async def get_dashboard_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取需要关注的警报
    """
    logger.info("fetching_dashboard_alerts", user_id=current_user.id)
    
    alerts = []
    
    # 高风险供应商警报
    high_risk_result = await db.execute(
        select(Supplier).where(
            Supplier.risk_level.in_(["high", "critical"]),
            Supplier.status == SupplierStatus.ACTIVE
        )
    )
    high_risk_suppliers = high_risk_result.scalars().all()
    
    for supplier in high_risk_suppliers:
        alerts.append({
            "type": "high_risk",
            "severity": "critical" if supplier.risk_level == "critical" else "high",
            "title": f"高风险供应商: {supplier.name}",
            "message": f"供应商 {supplier.name} 风险等级为 {supplier.risk_level}，建议审查",
            "supplier_id": str(supplier.id),
            "created_at": datetime.utcnow().isoformat(),
        })
    
    # 黑名单供应商警报
    blacklist_result = await db.execute(
        select(Supplier).where(
            Supplier.status == SupplierStatus.BLACKLIST
        )
    )
    blacklist_suppliers = blacklist_result.scalars().all()
    
    for supplier in blacklist_suppliers:
        alerts.append({
            "type": "blacklist",
            "severity": "critical",
            "title": f"黑名单供应商: {supplier.name}",
            "message": f"供应商 {supplier.name} 已被列入黑名单",
            "supplier_id": str(supplier.id),
            "created_at": datetime.utcnow().isoformat(),
        })
    
    return alerts


@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    获取系统健康状态
    """
    logger.info("fetching_system_health", user_id=current_user.id)
    
    # 模拟系统健康检查
    # 实际应该检查各个服务状态
    
    return {
        "overall_status": "healthy",
        "components": [
            {
                "name": "AI Brain",
                "status": "online",
                "load": 85,
                "last_check": datetime.utcnow().isoformat(),
            },
            {
                "name": "Database",
                "status": "online",
                "load": 62,
                "last_check": datetime.utcnow().isoformat(),
            },
            {
                "name": "API Gateway",
                "status": "online",
                "load": 45,
                "last_check": datetime.utcnow().isoformat(),
            },
            {
                "name": "Security",
                "status": "protected",
                "load": 100,
                "last_check": datetime.utcnow().isoformat(),
            },
        ],
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    获取最近活动记录
    """
    logger.info("fetching_recent_activity", user_id=current_user.id, limit=limit)
    
    # 查询最近创建的供应商
    result = await db.execute(
        select(Supplier)
        .order_by(Supplier.created_at.desc())
        .limit(limit)
    )
    suppliers = result.scalars().all()
    
    activities = []
    for supplier in suppliers:
        time_diff = datetime.utcnow() - supplier.created_at
        if time_diff.seconds < 3600:
            time_ago = f"{time_diff.seconds // 60}分钟前"
        elif time_diff.days == 0:
            time_ago = f"{time_diff.seconds // 3600}小时前"
        else:
            time_ago = f"{time_diff.days}天前"
        
        activities.append({
            "type": "supplier_created",
            "icon": "package",
            "event": f"新增供应商: {supplier.name}",
            "time": time_ago,
            "timestamp": supplier.created_at.isoformat(),
            "metadata": {
                "supplier_id": str(supplier.id),
                "business_type": supplier.business_type.value,
            }
        })
    
    return activities
