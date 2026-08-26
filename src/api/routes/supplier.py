"""
Supplier API Routes - Module 48

REST API endpoints for supplier management.

Architecture:
    API Endpoint
        ↓ (CRUD Dependency)
    SupplierCRUD
        ↓
    Database
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import SupplierStatus, BusinessType
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# ==================== Pydantic Schemas ====================


class SupplierCreateRequest(BaseModel):
    """供应商创建请求"""

    name: str = Field(..., min_length=1, max_length=200, description="供应商名称")
    code: Optional[str] = Field(None, max_length=50, description="供应商编码")
    legal_name: Optional[str] = Field(None, max_length=255, description="法定名称")
    business_type: BusinessType = Field(..., description="供应商类型")
    industry: Optional[str] = Field(None, max_length=100, description="所属行业")
    country: str = Field(..., max_length=100, description="国家")
    product_category: str = Field(..., max_length=100, description="产品类别")
    website: Optional[str] = Field(None, max_length=500, description="官网")
    description: Optional[str] = Field(None, description="简介")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    phone: Optional[str] = Field(None, max_length=50, description="电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    registered_capital: Optional[float] = Field(None, gt=0, description="注册资本")
    established_date: Optional[str] = Field(None, description="成立日期")


class SupplierUpdateRequest(BaseModel):
    """供应商更新请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    business_type: Optional[BusinessType] = None
    status: Optional[SupplierStatus] = None
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    country: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    registered_capital: Optional[float] = Field(None, gt=0)
    established_date: Optional[str] = None


class SupplierResponse(BaseModel):
    """供应商响应"""

    id: int
    name: str
    code: Optional[str]
    legal_name: Optional[str]
    business_type: str
    status: str
    industry: Optional[str]
    website: Optional[str]
    description: Optional[str]
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    registered_capital: Optional[float]
    established_date: Optional[str]
    employee_count: Optional[int]
    annual_revenue: Optional[float]
    product_category: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    """供应商列表分页响应"""
    items: List[SupplierResponse]
    total: int


class SupplierListResponse(BaseModel):
    """供应商列表分页响应"""
    items: List[SupplierResponse]
    total: int


class RiskAssessmentTriggerRequest(BaseModel):
    """触发风险评估请求"""
    assessor: str = Field(default="AI System", description="评估者")


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

    class Config:
        from_attributes = True


class ContactResponse(BaseModel):
    """联系人响应"""
    id: int
    supplier_id: int
    name: str
    position: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_primary: bool

    class Config:
        from_attributes = True


# ==================== API Endpoints ====================


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    request: SupplierCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "create")),
):
    """
    创建供应商

    需要权限: supplier:create
    """
    crud = SupplierCRUD(session)

    # 检查是否重复
    existing = await crud.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=400, detail=f"供应商名称已存在: {request.name}"
        )

    # 创建供应商
    supplier = await crud.create_supplier(
        name=request.name,
        code=request.code,
        legal_name=request.legal_name,
        country=request.country,
        product_category=request.product_category,
        business_type=request.business_type,
        industry=request.industry,
        website=request.website,
        description=request.description,
        address=request.address,
        phone=request.phone,
        email=request.email,
        registered_capital=request.registered_capital,
        established_date=request.established_date,
    )

    # 审计日志
    await AuditService.log(
        session=session,
        action=AuditAction.SUPPLIER_CREATED,
        resource_type="supplier",
        resource_id=str(supplier.id),
        status="success",
        user_id=current_user.id,
        details={"name": supplier.name, "type": supplier.business_type.value},
    )

    return SupplierResponse(
        id=str(supplier.id),
        name=supplier.name,
        code=supplier.code,
        legal_name=supplier.legal_name,
        business_type=supplier.business_type.value,
        status=supplier.status.value,
        industry=supplier.industry,
        website=supplier.website,
        description=supplier.description,
        country=supplier.country,
        province=supplier.province,
        city=supplier.city,
        address=supplier.address,
        phone=supplier.phone,
        email=supplier.email,
        registered_capital=supplier.registered_capital,
        established_date=supplier.established_date.isoformat() if supplier.established_date else None,
        employee_count=supplier.employee_count,
        annual_revenue=supplier.annual_revenue,
        product_category=supplier.product_category,
        created_at=supplier.created_at.isoformat(),
        updated_at=supplier.updated_at.isoformat(),
    )


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    status: Optional[SupplierStatus] = Query(None, description="按状态筛选"),
    business_type: Optional[BusinessType] = Query(None, description="按类型筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    查询供应商列表

    需要权限: supplier:read
    """
    crud = SupplierCRUD(session)
    suppliers = await crud.list_suppliers(
        status=status, business_type=business_type, skip=skip, limit=limit
    )

    # 获取总数
    from sqlalchemy import select, func
    from src.business.supplier.models import Supplier
    
    query = select(func.count()).select_from(Supplier)
    if status:
        query = query.where(Supplier.status == status)
    if business_type:
        query = query.where(Supplier.business_type == business_type)
    
    result = await session.execute(query)
    total = result.scalar_one()

    items = [
        SupplierResponse(
            id=str(s.id),
            name=s.name,
            code=s.code,
            legal_name=s.legal_name,
            business_type=s.business_type.value,
            status=s.status.value,
            industry=s.industry,
            website=s.website,
            description=s.description,
            country=s.country,
            province=s.province,
            city=s.city,
            address=s.address,
            phone=s.phone,
            email=s.email,
            registered_capital=s.registered_capital,
            established_date=s.established_date.isoformat() if s.established_date else None,
            employee_count=s.employee_count,
            annual_revenue=s.annual_revenue,
            product_category=s.product_category,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in suppliers
    ]
    
    return {"items": items, "total": total}


# ==================== 高级搜索端点 ====================

@router.get("/search")
async def search_suppliers(
    query: str = Query(..., description="搜索关键词"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    简单搜索供应商（按名称）
    
    需要权限: supplier:read
    """
    from sqlalchemy import select, or_
    from src.business.supplier.models import Supplier
    
    # 模糊搜索名称或法定名称
    stmt = select(Supplier).where(
        or_(
            Supplier.name.ilike(f"%{query}%"),
            Supplier.legal_name.ilike(f"%{query}%")
        )
    ).limit(100)
    
    result = await session.execute(stmt)
    suppliers = result.scalars().all()
    
    return [
        SupplierResponse(
            id=s.id,
            name=s.name,
            code=s.code,
            legal_name=s.legal_name,
            business_type=s.business_type.value,
            status=s.status.value,
            industry=s.industry,
            website=s.website,
            description=s.description,
            country=s.country,
            province=s.province,
            city=s.city,
            address=s.address,
            phone=s.phone,
            email=s.email,
            registered_capital=s.registered_capital,
            established_date=s.established_date.isoformat() if s.established_date else None,
            employee_count=s.employee_count,
            annual_revenue=s.annual_revenue,
            product_category=s.product_category,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in suppliers
    ]


@router.get("/advanced-search")
async def advanced_search_suppliers(
    name: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    business_type: Optional[str] = None,
    capital_min: Optional[float] = None,
    capital_max: Optional[float] = None,
    established_after: Optional[str] = None,
    established_before: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """高级搜索（多条件组合）"""
    crud = SupplierCRUD(session)
    
    # 构建筛选条件
    filters = {}
    if name:
        filters["name"] = name
    if status:
        filters["status"] = SupplierStatus(status)
    if country:
        filters["country"] = country
    if business_type:
        filters["business_type"] = BusinessType(business_type)
    if capital_min is not None:
        filters["capital_min"] = capital_min
    if capital_max is not None:
        filters["capital_max"] = capital_max
    if established_after:
        filters["established_after"] = datetime.fromisoformat(established_after)
    if established_before:
        filters["established_before"] = datetime.fromisoformat(established_before)
    
    result = await crud.advanced_search(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return result







@router.post("/batch", status_code=201)
async def batch_create_suppliers(
    suppliers: List[SupplierCreateRequest],
    validate: bool = True,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "create")),
):
    """批量创建供应商"""
    crud = SupplierCRUD(session)
    suppliers_data = [s.model_dump() for s in suppliers]
    result = await crud.batch_create(suppliers_data, validate=validate)
    return result


@router.put("/batch")
async def batch_update_suppliers(
    updates: List[dict],
    validate: bool = True,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """批量更新供应商"""
    crud = SupplierCRUD(session)
    result = await crud.batch_update(updates, validate=validate)
    return result


@router.delete("/batch")
async def batch_delete_suppliers(
    supplier_ids: List[int],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "delete")),
):
    """批量删除供应商"""
    crud = SupplierCRUD(session)
    result = await crud.batch_delete(supplier_ids)
    return result

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """获取单个供应商详情"""
    crud = SupplierCRUD(session)
    supplier = await crud.get_supplier(supplier_id)
    
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    return SupplierResponse(
        id=supplier.id,
        code=supplier.code,
        name=supplier.name,
        legal_name=supplier.legal_name,
        business_type=supplier.business_type.value,
        status=supplier.status.value,
        industry=supplier.industry,
        website=supplier.website,
        description=supplier.description,
        country=supplier.country,
        province=supplier.province,
        city=supplier.city,
        address=supplier.address,
        email=supplier.email,
        phone=supplier.phone,
        registered_capital=supplier.registered_capital,
        established_date=supplier.established_date.isoformat() if supplier.established_date else None,
        employee_count=supplier.employee_count,
        annual_revenue=supplier.annual_revenue,
        product_category=supplier.product_category,
        credit_rating=supplier.credit_rating,
        notes=supplier.notes,
        created_at=supplier.created_at.isoformat(),
        updated_at=supplier.updated_at.isoformat(),
    )


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    update_data: SupplierUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """更新供应商信息"""
    crud = SupplierCRUD(session)
    
    # 检查供应商是否存在
    existing_supplier = await crud.get_supplier(supplier_id)
    if not existing_supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 执行更新
    updated_supplier = await crud.update_supplier(
        supplier_id=supplier_id,
        **update_data.model_dump(exclude_unset=True)
    )
    
    return SupplierResponse(
        id=updated_supplier.id,
        code=updated_supplier.code,
        name=updated_supplier.name,
        legal_name=updated_supplier.legal_name,
        business_type=updated_supplier.business_type.value,
        status=updated_supplier.status.value,
        industry=updated_supplier.industry,
        website=updated_supplier.website,
        description=updated_supplier.description,
        country=updated_supplier.country,
        province=updated_supplier.province,
        city=updated_supplier.city,
        address=updated_supplier.address,
        email=updated_supplier.email,
        phone=updated_supplier.phone,
        registered_capital=updated_supplier.registered_capital,
        established_date=updated_supplier.established_date.isoformat() if updated_supplier.established_date else None,
        employee_count=updated_supplier.employee_count,
        annual_revenue=updated_supplier.annual_revenue,
        product_category=updated_supplier.product_category,
        credit_rating=updated_supplier.credit_rating,
        notes=updated_supplier.notes,
        created_at=updated_supplier.created_at.isoformat(),
        updated_at=updated_supplier.updated_at.isoformat(),
    )


@router.delete("/{supplier_id}", status_code=200)
async def delete_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "delete")),
):
    """删除供应商"""
    crud = SupplierCRUD(session)
    
    # 检查供应商是否存在
    existing_supplier = await crud.get_supplier(supplier_id)
    if not existing_supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 执行删除
    await crud.delete_supplier(supplier_id)
    return None


@router.get("/{supplier_id}/risk-history", response_model=List[RiskAssessmentResponse])
async def get_risk_history(
    supplier_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """获取供应商风险评估历史"""
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
            id=a.id,
            supplier_id=a.supplier_id,
            risk_level=a.risk_level.name,
            risk_score=a.overall_score,
            risk_factors=_risk_factors_from_model(a),
            assessment_date=a.assessment_date.isoformat(),
            assessor=current_user.username,
            recommendations=_recommendations_from_model(a),
            is_active=True,
        )
        for a in history
    ]

# ==================== 批量操作端点 ====================

@router.post("/import")
async def import_suppliers(
    file: bytes,
    file_type: str = "excel",
    validate: bool = True,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "create")),
):
    """导入供应商数据（Excel/CSV）"""
    from src.business.supplier.import_export import SupplierImportExport
    
    importer = SupplierImportExport(session)
    result = await importer.import_suppliers(file, file_type=file_type, validate=validate)
    return result


@router.get("/export")
async def export_suppliers(
    file_type: str = "excel",
    name: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """导出供应商数据（Excel/CSV）"""
    from src.business.supplier.import_export import SupplierImportExport
    from fastapi.responses import StreamingResponse
    import io
    
    # 构建筛选条件
    filters = {}
    if name:
        filters["name"] = name
    if status:
        filters["status"] = SupplierStatus(status)
    if country:
        filters["country"] = country
    
    exporter = SupplierImportExport(session)
    file_content = await exporter.export_suppliers(filters=filters if filters else None, file_type=file_type)
    
    # 返回文件
    filename = f"suppliers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{'xlsx' if file_type == 'excel' else 'csv'}"
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_type == "excel" else "text/csv"
    
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 联系人管理端点 ====================

@router.post("/{supplier_id}/contacts", response_model=ContactResponse, status_code=201)
async def add_contact(
    supplier_id: str,
    contact_data: dict,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """
    添加供应商联系人
    
    需要权限: supplier:update
    """
    from src.business.supplier.models import SupplierContact
    from sqlalchemy import select
    from src.business.supplier.models import Supplier
    
    # 验证供应商存在
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 创建联系人
    contact = SupplierContact(
        supplier_id=supplier_id,
        **contact_data
    )
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    
    return ContactResponse(
        id=str(contact.id),
        supplier_id=str(contact.supplier_id),
        name=contact.name,
        position=contact.position,
        phone=contact.phone,
        email=contact.email,
        is_primary=contact.is_primary,
        created_at=contact.created_at.isoformat(),
        updated_at=contact.updated_at.isoformat(),
    )


# ==================== 证书管理端点 ====================

@router.post("/{supplier_id}/certificates", status_code=201)
async def add_certificate(
    supplier_id: str,
    certificate_data: dict,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """
    添加供应商证书
    
    需要权限: supplier:update
    """
    from src.business.supplier.models import SupplierCertificate
    from sqlalchemy import select
    from src.business.supplier.models import Supplier
    from datetime import datetime
    
    # 验证供应商存在
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 处理日期字段
    if "issue_date" in certificate_data and isinstance(certificate_data["issue_date"], str):
        certificate_data["issue_date"] = datetime.fromisoformat(certificate_data["issue_date"].replace("Z", "+00:00"))
    if "expiry_date" in certificate_data and isinstance(certificate_data["expiry_date"], str):
        certificate_data["expiry_date"] = datetime.fromisoformat(certificate_data["expiry_date"].replace("Z", "+00:00"))
    
    # 创建证书
    certificate = SupplierCertificate(
        supplier_id=supplier_id,
        **certificate_data
    )
    session.add(certificate)
    await session.commit()
    await session.refresh(certificate)
    
    return {
        "id": str(certificate.id),
        "supplier_id": str(certificate.supplier_id),
        "certificate_type": certificate.certificate_type,
        "certificate_name": certificate.certificate_name,
        "certificate_number": certificate.certificate_number,
        "issuing_authority": certificate.issuing_authority,
        "issuing_country": certificate.issuing_country,
        "issue_date": certificate.issue_date.isoformat() if certificate.issue_date else None,
        "expiry_date": certificate.expiry_date.isoformat() if certificate.expiry_date else None,
        "is_verified": certificate.is_verified,
        "created_at": certificate.created_at.isoformat(),
        "updated_at": certificate.updated_at.isoformat(),
    }
