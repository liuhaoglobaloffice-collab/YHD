"""
S3 自动获客 + 供应商分析 API.

提供获客引擎、CRM 线索池、跟进提醒、海关数据、
供应商发现与供应商多维分析端点。
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.crm.analysis import SupplierAnalysisService
from src.crm.engines import (
    CustomsDataProvider,
    LeadAcquisitionEngine,
    SupplierDiscoveryEngine,
)
from src.crm.models import (
    CustomsRecord,
    Lead,
    LeadActivity,
    LeadSource,
    SupplierAnalysisReport,
    SupplierInquiry,
)
from src.crm.service import LeadService
from src.database.models import AiCostRecordModel
from src.identity.audit import AuditService
from src.identity.models import AccountType, User
from src.identity.visibility import DataScopeFilter, visible_user_ids
from src.integrations.models import PlatformMessage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/crm", tags=["crm"])


# ==================== Schemas ====================


class LeadCreate(BaseModel):
    source: str = Field("manual")
    source_detail: Optional[str] = None
    source_type: Optional[str] = Field(None, description="REAL / MOCK / NOT_CONFIGURED")
    name: str = Field(..., min_length=1)
    company: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    wechat: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    product_interest: Optional[str] = None
    estimated_value: Optional[float] = None
    score: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    owner_user_id: Optional[int] = Field(
        None, description="仅主账号可为名下子账号代建（V4），缺省归属本人"
    )


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    wechat: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    product_interest: Optional[str] = None
    estimated_value: Optional[float] = None
    score: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    quote_amount: Optional[float] = None
    won_amount: Optional[float] = None
    expected_close_at: Optional[datetime] = None
    lost_reason: Optional[str] = None


class ActivityCreate(BaseModel):
    activity_type: str = Field(..., description="call/email/message/meeting/note")
    content: str = Field(..., min_length=1)
    result: Optional[str] = None
    next_follow_up_at: Optional[datetime] = None


class AcquisitionRequest(BaseModel):
    sources: List[str] = Field(default_factory=lambda: ["social", "google", "customs"])
    keywords: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=50)
    save_to_pool: bool = True


class CustomsSearchRequest(BaseModel):
    product: Optional[str] = None
    country: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    save: bool = True


class SupplierDiscoverRequest(BaseModel):
    product: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)


class SupplierAnalyzeRequest(BaseModel):
    supplier_name: str = Field(..., min_length=1)
    product_category: Optional[str] = None
    supplier_data: Optional[Dict[str, Any]] = None
    supplier_id: Optional[int] = None


class InquiryCreate(BaseModel):
    """供应商询价录入。"""

    supplier_name: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    quantity: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    currency: str = Field("USD", min_length=1, max_length=10)
    lead_time: Optional[str] = None
    payment: Optional[str] = None
    quality_note: Optional[str] = None
    note: Optional[str] = None


class QuotationRequest(BaseModel):
    """报价单生成参数（缺省取值自线索的报价金额）。"""

    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[float] = Field(None, ge=0)
    moq: Optional[str] = None
    lead_time: Optional[str] = None
    payment: Optional[str] = None
    currency: str = Field("USD", min_length=1, max_length=10)
    freight: Optional[float] = Field(None, ge=0)
    valid_days: int = Field(15, ge=1, le=90)


# ==================== 序列化 ====================

LEAD_STATUS_LABELS = {
    "new": "新线索",
    "contacted": "已联系",
    "qualified": "已确认意向",
    "proposal": "方案/报价中",
    "won": "成交",
    "lost": "流失",
}
LEAD_SOURCE_LABELS = {
    "social": "社媒",
    "google": "谷歌搜索",
    "customs": "海关数据",
    "manual": "手动",
    "import": "导入",
}


def _lead_out(l: Lead) -> Dict[str, Any]:
    return {
        "id": l.id,
        "source": l.source.value,
        "source_label": LEAD_SOURCE_LABELS.get(l.source.value, l.source.value),
        "source_detail": l.source_detail,
        "source_type": l.source_type,
        "name": l.name,
        "company": l.company,
        "country": l.country,
        "city": l.city,
        "industry": l.industry,
        "phone": l.phone,
        "email": l.email,
        "whatsapp": l.whatsapp,
        "wechat": l.wechat,
        "linkedin": l.linkedin,
        "website": l.website,
        "product_interest": l.product_interest,
        "estimated_value": l.estimated_value,
        "score": l.score,
        "status": l.status.value,
        "status_label": LEAD_STATUS_LABELS.get(l.status.value, l.status.value),
        "priority": l.priority.value,
        "quote_amount": l.quote_amount,
        "won_amount": l.won_amount,
        "expected_close_at": l.expected_close_at.isoformat() if l.expected_close_at else None,
        "lost_reason": l.lost_reason,
        "next_follow_up_at": l.next_follow_up_at.isoformat() if l.next_follow_up_at else None,
        "last_activity_at": l.last_activity_at.isoformat() if l.last_activity_at else None,
        "notes": l.notes,
        "created_at": l.created_at.isoformat(),
        "updated_at": l.updated_at.isoformat(),
    }


def _activity_out(a: LeadActivity) -> Dict[str, Any]:
    return {
        "id": a.id,
        "lead_id": a.lead_id,
        "activity_type": a.activity_type.value,
        "content": a.content,
        "result": a.result,
        "created_at": a.created_at.isoformat(),
    }


def _report_out(r: SupplierAnalysisReport) -> Dict[str, Any]:
    return {
        "id": r.id,
        "supplier_id": r.supplier_id,
        "supplier_name": r.supplier_name,
        "product_category": r.product_category,
        "risk_level": r.risk_level,
        "risk_score": r.risk_score,
        "risk_summary": r.risk_summary,
        "price_level": r.price_level,
        "price_score": r.price_score,
        "price_summary": r.price_summary,
        "capacity_level": r.capacity_level,
        "capacity_score": r.capacity_score,
        "capacity_summary": r.capacity_summary,
        "overall_score": r.overall_score,
        "overall_level": r.overall_level,
        "report": r.report,
        "recommendations": r.recommendations or [],
        "analysis_method": r.analysis_method,
        "created_at": r.created_at.isoformat(),
    }


def _customs_out(c: CustomsRecord) -> Dict[str, Any]:
    return {
        "id": c.id,
        "hs_code": c.hs_code,
        "product": c.product,
        "product_desc": c.product_desc,
        "importer_name": c.importer_name,
        "importer_country": c.importer_country,
        "exporter_name": c.exporter_name,
        "exporter_country": c.exporter_country,
        "quantity": c.quantity,
        "unit": c.unit,
        "value": c.value,
        "trade_date": c.trade_date.isoformat() if c.trade_date else None,
        "created_at": c.created_at.isoformat(),
    }


# ==================== 获客引擎 ====================


@router.post("/acquisition/run")
async def run_acquisition(
    request: AcquisitionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "create")),
):
    """运行自动获客引擎（社媒/谷歌/海关），推荐潜在客户并可入库线索池。"""
    engine = LeadAcquisitionEngine()
    result = await engine.run(
        sources=request.sources,
        keywords=request.keywords,
        limit=request.limit,
    )
    leads = result["leads"]

    saved = {"created": 0, "skipped": 0}
    if request.save_to_pool and leads:
        service = LeadService(session)
        items = [
            {
                **{k: v for k, v in l.items() if k in (
                    "name", "company", "country", "city", "industry", "email",
                    "phone", "whatsapp", "wechat", "linkedin", "website",
                    "product_interest", "score", "source_type",
                )},
                "source": l.get("source", "social"),
                "source_detail": l.get("source_detail"),
            }
            for l in leads
        ]
        saved = await service.create_leads_batch(items, current_user.id, current_user.tenant_id)

    await AuditService.log_success(
        session=session,
        action="run_acquisition",
        resource_type="lead",
        user_id=current_user.id,
        details={"sources": request.sources, "found": len(leads), **saved},
    )
    return {"leads": leads, "stats": result["stats"], "saved": saved}


# ==================== 线索池 CRM ====================


@router.get("/leads/stats")
async def lead_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """线索池统计。"""
    service = LeadService(session)
    return await service.stats(visible_user_ids(current_user))


@router.get("/leads")
async def list_leads(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    follow_up: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """线索池列表（支持筛选/搜索/待跟进）。"""
    service = LeadService(session)
    result = await service.list_leads(
        user_ids=visible_user_ids(current_user),
        status=status,
        source=source,
        keyword=keyword,
        follow_up=follow_up,
        page=page,
        page_size=page_size,
    )
    from src.core.masking import mask_dict

    items = [mask_dict(_lead_out(l)) for l in result["items"]]
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("/leads", status_code=201)
async def create_lead(
    request: LeadCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "create")),
):
    """手动添加线索（主账号可为名下子账号代建）。"""
    service = LeadService(session)
    data = request.model_dump(exclude_none=True)
    owner_id = data.pop("owner_user_id", None)
    if owner_id is not None:
        # 仅主账号可为名下子账号代建
        if current_user.account_type != AccountType.OWNER and not getattr(
            current_user, "is_superuser", False
        ):
            raise HTTPException(status_code=403, detail="只有主账号可以为子账号代建线索")
        target = await session.execute(
            select(User).where(
                User.id == owner_id,
                User.account_type == AccountType.SUB,
                User.parent_user_id == current_user.id,
            )
        )
        if not target.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="只能为你的子账号代建线索")
    else:
        owner_id = current_user.id
    lead = await service.create_lead(data, owner_id, current_user.tenant_id)
    return _lead_out(lead)


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """线索详情 + 跟进记录。"""
    service = LeadService(session)
    lead = await service.get_lead(lead_id, visible_user_ids(current_user))
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    activities = await service.list_activities(lead_id)
    return {**_lead_out(lead), "activities": [_activity_out(a) for a in activities]}


@router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    request: LeadUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "update")),
):
    """更新线索（状态/优先级/跟进时间等）。"""
    service = LeadService(session)
    lead = await service.get_lead(lead_id, {current_user.id})
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    lead = await service.update_lead(lead, request.model_dump(exclude_none=True))
    return _lead_out(lead)


@router.delete("/leads/{lead_id}", status_code=200)
async def delete_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "delete")),
):
    """删除线索。"""
    service = LeadService(session)
    if not await service.delete_lead(lead_id, current_user.id):
        raise HTTPException(status_code=404, detail="线索不存在")
    return {"ok": True}


@router.get("/leads/export")
async def export_leads_csv(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """导出线索为 CSV 文件。"""
    from src.identity.visibility import visible_user_ids
    from fastapi.responses import PlainTextResponse

    service = LeadService(session)
    csv_content = await service.export_csv(visible_user_ids(current_user))
    return PlainTextResponse(csv_content, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=leads.csv"})


class AssignRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)


@router.post("/leads/{lead_id}/assign")
async def assign_lead(
    lead_id: int,
    request: AssignRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "update")),
):
    """将线索分配给 AI 员工。"""
    service = LeadService(session)
    try:
        lead = await service.assign_to_employee(lead_id, request.employee_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _lead_out(lead)


class BatchAssignRequest(BaseModel):
    lead_ids: List[int] = Field(..., min_length=1)
    employee_id: str = Field(..., min_length=1)


@router.post("/leads/batch-assign")
async def batch_assign_leads(
    request: BatchAssignRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "update")),
):
    """批量分配线索给 AI 员工。"""
    service = LeadService(session)
    count = await service.batch_assign(request.lead_ids, request.employee_id, current_user.id)
    return {"assigned": count}


@router.post("/leads/{lead_id}/activities", status_code=201)
async def add_activity(
    lead_id: int,
    request: ActivityCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "update")),
):
    """添加跟进记录（可设置下次跟进时间）。"""
    service = LeadService(session)
    try:
        activity = await service.add_activity(
            lead_id=lead_id,
            owner_user_id=current_user.id,
            activity_type=request.activity_type,
            content=request.content,
            result=request.result,
            next_follow_up_at=request.next_follow_up_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _activity_out(activity)


# ==================== 海关数据 ====================


@router.post("/customs/search")
async def customs_search(
    request: CustomsSearchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("customs", "read")),
):
    """查询海关进出口数据，可选保存。"""
    provider = CustomsDataProvider()
    records = await provider.search(request.product, request.country, request.limit)

    saved = 0
    if request.save:
        for r in records:
            rec = CustomsRecord(
                hs_code=r.get("hs_code"),
                product=r.get("product", ""),
                product_desc=r.get("product_desc"),
                importer_name=r.get("importer_name"),
                importer_country=r.get("importer_country"),
                exporter_name=r.get("exporter_name"),
                exporter_country=r.get("exporter_country"),
                quantity=r.get("quantity"),
                unit=r.get("unit"),
                value=r.get("value"),
                trade_date=datetime.fromisoformat(r["trade_date"]) if r.get("trade_date") else None,
                source="customs-api",
                owner_user_id=current_user.id,
                tenant_id=current_user.tenant_id,
            )
            session.add(rec)
            saved += 1
        await session.commit()
    return {"records": records, "saved": saved}


@router.get("/customs")
async def list_customs(
    product: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("customs", "read")),
):
    """查看已保存的海关数据。"""
    stmt = select(CustomsRecord).where(
        CustomsRecord.owner_user_id.in_(list(visible_user_ids(current_user)))
    )
    if product:
        stmt = stmt.where(CustomsRecord.product.contains(product))
    stmt = stmt.order_by(CustomsRecord.created_at.desc()).limit(limit)
    records = list((await session.execute(stmt)).scalars().all())
    return [_customs_out(r) for r in records]


# ==================== 供应商发现与分析 ====================


@router.post("/suppliers/discover")
async def discover_suppliers(
    request: SupplierDiscoverRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """发现国内供应商。"""
    engine = SupplierDiscoveryEngine()
    results = await engine.discover(request.product, request.limit)
    return {"suppliers": results, "total": len(results)}


@router.post("/suppliers/analyze")
async def analyze_supplier(
    request: SupplierAnalyzeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """生成供应商多维分析报告（风险/价格/产能）。"""
    service = SupplierAnalysisService(session)
    report = await service.generate_report(
        supplier_name=request.supplier_name,
        product_category=request.product_category,
        supplier_data=request.supplier_data,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
        supplier_id=request.supplier_id,
    )
    return _report_out(report)


@router.get("/suppliers/analysis")
async def list_supplier_analysis(
    supplier_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """查看供应商分析报告列表。"""
    service = SupplierAnalysisService(session)
    reports = await service.list_reports(
        limit=limit, supplier_id=supplier_id, user_ids=visible_user_ids(current_user)
    )
    return [_report_out(r) for r in reports]


@router.get("/suppliers/{supplier_id}/analysis")
async def analyze_supplier_by_id(
    supplier_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """对已有供应商（按 ID）生成/查看分析报告。"""
    from src.business.supplier.models import Supplier

    user_ids = visible_user_ids(current_user)
    result = await session.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.created_by.in_(list(user_ids)),
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")

    service = SupplierAnalysisService(session)
    latest = await service.get_latest(supplier_id, user_ids)
    if latest:
        return _report_out(latest)

    supplier_data = {
        "country": supplier.country,
        "province": supplier.province,
        "city": supplier.city,
        "business_type": supplier.business_type.value if supplier.business_type else None,
        "registered_capital": supplier.registered_capital,
        "employee_count": supplier.employee_count,
        "annual_revenue": supplier.annual_revenue,
        "established_date": supplier.established_date,
        "has_iso9001": supplier.has_iso9001,
        "has_export_license": supplier.has_export_license,
        "cooperation_years": supplier.cooperation_years,
        "risk_score": supplier.risk_score,
        "status": supplier.status.value if supplier.status else None,
    }
    report = await service.generate_report(
        supplier_name=supplier.name,
        product_category=supplier.product_category,
        supplier_data=supplier_data,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
        supplier_id=supplier.id,
    )
    return _report_out(report)


# ==================== 供应商询价 / 比价（V3） ====================


def _inquiry_out(q: SupplierInquiry) -> Dict[str, Any]:
    return {
        "id": q.id,
        "supplier_name": q.supplier_name,
        "product": q.product,
        "quantity": q.quantity,
        "unit_price": q.unit_price,
        "currency": q.currency or "USD",
        "lead_time": q.lead_time,
        "payment": q.payment,
        "quality_note": q.quality_note,
        "note": q.note,
        "created_by": q.created_by,
        "created_at": q.created_at.isoformat(),
    }


@router.post("/supplier-inquiries", status_code=201)
async def create_supplier_inquiry(
    request: InquiryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """录入一条供应商询价（用于比价）。"""
    inquiry = SupplierInquiry(
        supplier_name=request.supplier_name.strip(),
        product=request.product.strip(),
        quantity=request.quantity,
        unit_price=request.unit_price,
        currency=request.currency or "USD",
        lead_time=request.lead_time,
        payment=request.payment,
        quality_note=request.quality_note,
        note=request.note,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    session.add(inquiry)
    await session.commit()
    await session.refresh(inquiry)
    return _inquiry_out(inquiry)


@router.get("/supplier-inquiries")
async def list_supplier_inquiries(
    product: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """询价记录列表（可见范围）。"""
    user_ids = visible_user_ids(current_user)
    stmt = select(SupplierInquiry).where(SupplierInquiry.created_by.in_(list(user_ids)))
    if product:
        stmt = stmt.where(SupplierInquiry.product.contains(product))
    stmt = stmt.order_by(SupplierInquiry.created_at.desc()).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    return [_inquiry_out(r) for r in rows]


@router.get("/supplier-inquiries/compare")
async def compare_supplier_inquiries(
    product: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """按产品比价：列出各供应商报价并推荐最优。"""
    user_ids = visible_user_ids(current_user)
    stmt = (
        select(SupplierInquiry)
        .where(
            SupplierInquiry.created_by.in_(list(user_ids)),
            SupplierInquiry.product.contains(product),
        )
        .order_by(SupplierInquiry.unit_price.asc())
    )
    rows = list((await session.execute(stmt)).scalars().all())
    priced = [r for r in rows if r.unit_price is not None]
    cheapest = priced[0] if priced else None
    return {
        "product": product,
        "count": len(rows),
        "cheapest": _inquiry_out(cheapest) if cheapest else None,
        "items": [_inquiry_out(r) for r in rows],
    }


# ==================== 报价单生成（V3） ====================


@router.post("/leads/{lead_id}/quotation")
async def generate_quotation(
    lead_id: int,
    request: QuotationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """基于线索的报价金额生成报价单（可复制给客户）。"""
    service = LeadService(session)
    lead = await service.get_lead(lead_id, visible_user_ids(current_user))
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")

    quantity = request.quantity or 1
    unit_price = request.unit_price
    if unit_price is None and lead.quote_amount:
        unit_price = round(lead.quote_amount / quantity, 2)
    total = round((unit_price or 0) * quantity + (request.freight or 0), 2)
    valid_until = (datetime.now(UTC) + timedelta(days=request.valid_days)).strftime("%Y-%m-%d")
    missing = []
    if unit_price is None:
        missing.append("单价/报价金额")
    if not lead.product_interest:
        missing.append("产品")

    quotation = {
        "lead_id": lead.id,
        "company": lead.company or lead.name,
        "contact": lead.name,
        "email": lead.email,
        "whatsapp": lead.whatsapp,
        "country": lead.country,
        "product": lead.product_interest or request.moq or "产品待确认",
        "quantity": quantity,
        "currency": request.currency,
        "unit_price": unit_price,
        "freight": request.freight,
        "total": total,
        "moq": request.moq,
        "lead_time": request.lead_time or "待确认",
        "payment": request.payment or "30% T/T 定金，70% 发货前付清",
        "valid_until": valid_until,
        "notes": request.lead_time or None,
        "missing_fields": missing,
    }
    return quotation


# ==================== 外贸周报（V3） ====================


async def _build_weekly_report(
    session: AsyncSession, user_ids, days: int
) -> Dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)
    user_ids_list = list(user_ids)

    # 线索 & 漏斗
    leads = list(
        (
            await session.execute(
                select(Lead).where(Lead.owner_user_id.in_(user_ids_list))
            )
        ).scalars().all()
    )
    new_leads = [l for l in leads if l.created_at >= since]
    by_source: Dict[str, int] = {}
    for l in new_leads:
        key = l.source.value if hasattr(l.source, "value") else str(l.source)
        by_source[key] = by_source.get(key, 0) + 1
    quoted = sum(1 for l in leads if l.quote_amount)
    won = [l for l in leads if l.status.value == "won"]
    won_amount = sum(l.won_amount or 0 for l in won)
    lost = [l for l in leads if l.status.value == "lost"]
    follow_up_due = sum(1 for l in leads if l.next_follow_up_at and l.next_follow_up_at <= datetime.now(UTC))
    lost_reasons: Dict[str, int] = {}
    for l in lost:
        if l.lost_reason:
            r = l.lost_reason.strip()
            if r:
                lost_reasons[r] = lost_reasons.get(r, 0) + 1

    # 平台消息
    msg_rows = list(
        (
            await session.execute(
                select(PlatformMessage).where(
                    PlatformMessage.owner_user_id.in_(user_ids_list),
                    PlatformMessage.created_at >= since,
                )
            )
        ).scalars().all()
    )
    msg_sent = sum(1 for m in msg_rows if m.direction.value == "outbound")
    msg_received = sum(1 for m in msg_rows if m.direction.value == "inbound")

    # 供应商分析报告
    reports = list(
        (
            await session.execute(
                select(SupplierAnalysisReport).where(
                    SupplierAnalysisReport.created_by.in_(user_ids_list),
                    SupplierAnalysisReport.created_at >= since,
                )
            )
        ).scalars().all()
    )

    # 询价记录
    inquiries = list(
        (
            await session.execute(
                select(SupplierInquiry).where(
                    SupplierInquiry.created_by.in_(user_ids_list),
                    SupplierInquiry.created_at >= since,
                )
            )
        ).scalars().all()
    )

    # AI 成本
    cost_rows = list(
        (
            await session.execute(
                select(AiCostRecordModel).where(
                    AiCostRecordModel.user_id.in_(user_ids_list),
                    AiCostRecordModel.created_at >= since,
                )
            )
        ).scalars().all()
    )
    ai_cost = round(sum(r.cost_usd or 0 for r in cost_rows), 4)
    ai_calls = len(cost_rows)

    report = {
        "days": days,
        "period": f"{since.strftime('%Y-%m-%d')} ~ {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "leads": {
            "new_total": len(new_leads),
            "by_source": by_source,
            "follow_up_due": follow_up_due,
        },
        "funnel": {
            "quoted": quoted,
            "won_count": len(won),
            "won_amount": round(won_amount, 2),
            "lost_count": len(lost),
            "lost_reasons": dict(
                sorted(lost_reasons.items(), key=lambda kv: kv[1], reverse=True)[:5]
            ),
        },
        "messages": {"sent": msg_sent, "received": msg_received},
        "supplier_reports": len(reports),
        "inquiries": len(inquiries),
        "ai": {"calls": ai_calls, "cost_usd": ai_cost},
    }
    # LLM 摘要（不可用回退模板）
    report["summary"] = await _ai_weekly_summary(report)
    return report


async def _ai_weekly_summary(report: Dict[str, Any]) -> str:
    try:
        from src.ai.gateway import get_gateway
        from src.ai.providers import ProviderType

        provider_str = __import__("os").getenv("LLM_PROVIDER", "mock").lower().strip()
        if provider_str == "openai":
            provider, model = ProviderType.OPENAI, __import__("os").getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        elif provider_str == "ollama":
            provider, model = ProviderType.OLLAMA, __import__("os").getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
        else:
            raise RuntimeError("无 LLM，使用模板摘要")
        prompt = (
            "你是外贸业务复盘助手。根据以下一周经营数据，用中文输出 4-6 条要点式周报总结"
            "（含趋势、风险、下周建议），不要客套：\n"
            f"{report}"
        )
        resp = await get_gateway().complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id="weekly-report",
            temperature=0.4,
            max_tokens=600,
        )
        text = (resp.content or "").strip()
        if text:
            return text
    except Exception:
        pass
    return (
        f"本周新增线索 {report['leads']['new_total']} 条"
        f"（新增询盘报价客户 {report['funnel']['quoted']} 家，成交 {report['funnel']['won_count']} 单"
        f" {report['funnel']['won_amount']} USD）；"
        f"平台消息发送 {report['messages']['sent']} 条、接收 {report['messages']['received']} 条；"
        f"新增供应商分析 {report['supplier_reports']} 份、询价记录 {report['inquiries']} 条；"
        f"AI 调用 {report['ai']['calls']} 次，成本 ${report['ai']['cost_usd']}；"
        f"待跟进 {report['leads']['follow_up_due']} 条"
        + (f"，流失 {report['funnel']['lost_count']} 单（{report['funnel']['lost_reasons']}）" if report['funnel']['lost_count'] else "")
        + "。建议优先跟进待跟进客户并复盘流失原因。"
    )


@router.get("/weekly-report")
async def weekly_report(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("lead", "read")),
):
    """外贸周报：聚合线索/漏斗/平台消息/供应商/AI 成本并生成总结。"""
    report = await _build_weekly_report(session, visible_user_ids(current_user), days)
    return report
