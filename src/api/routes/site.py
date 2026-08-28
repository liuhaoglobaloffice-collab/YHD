"""
S4 独立站 + SEO API.

提供独立站配置管理、内容发布、SEO 关键词分析/内容生成/排名跟踪端点。
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.visibility import visible_user_ids
from src.site_os.models import KeywordRank, SEOContent, SiteConfig, SitePage
from src.site_os.seo import SEOEngine
from src.site_os.service import SiteService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/site", tags=["site"])


# ==================== Schemas ====================


class SiteCreate(BaseModel):
    domain: str = Field(..., min_length=1)
    name: Optional[str] = None
    platform: str = "shopify"
    default_meta_title: Optional[str] = None
    default_meta_description: Optional[str] = None
    default_lang: Optional[str] = "en"
    target_countries: Optional[List[str]] = None
    target_keywords: Optional[List[str]] = None
    credentials: Optional[Dict[str, Any]] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    platform: Optional[str] = None
    default_meta_title: Optional[str] = None
    default_meta_description: Optional[str] = None
    default_lang: Optional[str] = None
    target_countries: Optional[List[str]] = None
    target_keywords: Optional[List[str]] = None


class PageCreate(BaseModel):
    title: str = Field(..., min_length=1)
    slug: Optional[str] = None
    content: Optional[str] = None
    content_type: str = "page"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[List[str]] = None
    canonical_url: Optional[str] = None
    status: str = "draft"


class PageUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[List[str]] = None
    canonical_url: Optional[str] = None
    status: Optional[str] = None


class KeywordAnalyzeRequest(BaseModel):
    keywords: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=50)


class SEOContentRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    content_type: str = "blog"
    save: bool = True


class RankTrackRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1)
    save: bool = True


# ==================== 序列化 ====================


def _site_out(s: SiteConfig) -> Dict[str, Any]:
    return {
        "id": s.id,
        "domain": s.domain,
        "name": s.name,
        "platform": s.platform,
        "status": s.status,
        "default_meta_title": s.default_meta_title,
        "default_meta_description": s.default_meta_description,
        "default_lang": s.default_lang,
        "target_countries": s.target_countries or [],
        "target_keywords": s.target_keywords or [],
        "created_at": s.created_at.isoformat(),
    }


def _page_out(p: SitePage) -> Dict[str, Any]:
    return {
        "id": p.id,
        "site_id": p.site_id,
        "title": p.title,
        "slug": p.slug,
        "content": p.content,
        "content_type": p.content_type,
        "meta_title": p.meta_title,
        "meta_description": p.meta_description,
        "keywords": p.keywords or [],
        "canonical_url": p.canonical_url,
        "status": p.status.value,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "views": p.views,
        "conversions": p.conversions,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


def _rank_out(r: KeywordRank) -> Dict[str, Any]:
    return {
        "id": r.id,
        "keyword": r.keyword,
        "rank": r.rank,
        "previous_rank": r.previous_rank,
        "trend": r.trend.value,
        "search_volume": r.search_volume,
        "url": r.url,
        "country": r.country,
        "checked_at": r.checked_at.isoformat(),
    }


def _content_out(c: SEOContent) -> Dict[str, Any]:
    return {
        "id": c.id,
        "keyword": c.keyword,
        "title": c.title,
        "meta_description": c.meta_description,
        "outline": c.outline,
        "content": c.content,
        "content_type": c.content_type,
        "suggested_slug": c.suggested_slug,
        "suggested_tags": c.suggested_tags or [],
        "search_intent": c.search_intent,
        "method": c.method,
        "created_at": c.created_at.isoformat(),
    }


# ==================== 独立站配置 ====================


@router.post("/sites", response_model=Dict[str, Any], status_code=201)
async def create_site(
    request: SiteCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "create")),
):
    """创建独立站配置。"""
    service = SiteService(session)
    site = await service.create_site(request.model_dump(exclude_none=True), current_user.id, current_user.tenant_id)
    await AuditService.log_success(
        session=session,
        action="create_site",
        resource_type="site",
        user_id=current_user.id,
        resource_id=str(site.id),
        details={"domain": site.domain},
    )
    return _site_out(site)


@router.get("/sites")
async def list_sites(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "read")),
):
    """列出独立站。"""
    service = SiteService(session)
    sites = await service.list_sites(visible_user_ids(current_user))
    return {"items": [_site_out(s) for s in sites], "total": len(sites)}


@router.patch("/sites/{site_id}", response_model=Dict[str, Any])
async def update_site(
    site_id: int,
    request: SiteUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "update")),
):
    """更新独立站配置。"""
    service = SiteService(session)
    site = await service.get_site(site_id, {current_user.id})
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")
    site = await service.update_site(site, request.model_dump(exclude_none=True))
    return _site_out(site)


@router.delete("/sites/{site_id}", status_code=200)
async def delete_site(
    site_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "delete")),
):
    """删除独立站。"""
    service = SiteService(session)
    if not await service.delete_site(site_id, current_user.id):
        raise HTTPException(status_code=404, detail="站点不存在")
    return {"ok": True}


@router.get("/sites/{site_id}/stats")
async def site_stats(
    site_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "read")),
):
    """独立站访问/转化统计。"""
    service = SiteService(session)
    if not await service.get_site(site_id, visible_user_ids(current_user)):
        raise HTTPException(status_code=404, detail="站点不存在")
    return await service.site_stats(site_id)


# ==================== 页面管理 ====================


@router.post("/sites/{site_id}/pages", response_model=Dict[str, Any], status_code=201)
async def create_page(
    site_id: int,
    request: PageCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "create")),
):
    """创建站点页面（草稿或直接发布）。"""
    service = SiteService(session)
    if not await service.get_site(site_id, {current_user.id}):
        raise HTTPException(status_code=404, detail="站点不存在")
    page = await service.create_page(site_id, request.model_dump(exclude_none=True), current_user.id, current_user.tenant_id)
    return _page_out(page)


@router.get("/sites/{site_id}/pages")
async def list_pages(
    site_id: int,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "read")),
):
    """列出站点页面。"""
    service = SiteService(session)
    if not await service.get_site(site_id, visible_user_ids(current_user)):
        raise HTTPException(status_code=404, detail="站点不存在")
    result = await service.list_pages(site_id, status, page, page_size)
    return {"items": [_page_out(p) for p in result["items"]], "total": result["total"]}


@router.patch("/sites/{site_id}/pages/{page_id}", response_model=Dict[str, Any])
async def update_page(
    site_id: int,
    page_id: int,
    request: PageUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "update")),
):
    """更新站点页面。"""
    service = SiteService(session)
    if not await service.get_site(site_id, {current_user.id}):
        raise HTTPException(status_code=404, detail="站点不存在")
    page = await service.get_page(page_id)
    if not page or page.site_id != site_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    page = await service.update_page(page, request.model_dump(exclude_none=True))
    return _page_out(page)


@router.post("/sites/{site_id}/pages/{page_id}/publish", response_model=Dict[str, Any])
async def publish_page(
    site_id: int,
    page_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "update")),
):
    """发布站点页面。"""
    service = SiteService(session)
    if not await service.get_site(site_id, {current_user.id}):
        raise HTTPException(status_code=404, detail="站点不存在")
    page = await service.get_page(page_id)
    if not page or page.site_id != site_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    page = await service.publish_page(page)
    return _page_out(page)


@router.delete("/sites/{site_id}/pages/{page_id}", status_code=200)
async def delete_page(
    site_id: int,
    page_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("site", "delete")),
):
    """删除站点页面。"""
    service = SiteService(session)
    if not await service.get_site(site_id, {current_user.id}):
        raise HTTPException(status_code=404, detail="站点不存在")
    if not await service.delete_page(page_id):
        raise HTTPException(status_code=404, detail="页面不存在")
    return {"ok": True}


# ==================== SEO 引擎 ====================


@router.post("/seo/keywords/analyze")
async def analyze_keywords(
    request: KeywordAnalyzeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("seo", "read")),
):
    """关键词分析与扩展。"""
    engine = SEOEngine()
    results = await engine.analyze_keywords(request.keywords, request.limit)
    return {"keywords": results, "total": len(results)}


@router.post("/seo/content/generate")
async def generate_content(
    request: SEOContentRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("seo", "read")),
):
    """生成 SEO 内容建议（AI/规则模板）。"""
    engine = SEOEngine()
    data = await engine.generate_content(request.keyword, current_user.username, request.content_type)
    saved_id = None
    if request.save:
        service = SiteService(session)
        sites = await service.list_sites({current_user.id})
        if sites:
            obj = await service.save_seo_content(sites[0].id, data, current_user.id, current_user.tenant_id)
            saved_id = obj.id
    return {**data, "saved_id": saved_id}


@router.post("/seo/rankings/track")
async def track_rankings(
    request: RankTrackRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("seo", "read")),
):
    """跟踪关键词排名。"""
    engine = SEOEngine()
    results = await engine.track_rankings(request.keywords)
    if request.save:
        service = SiteService(session)
        sites = await service.list_sites({current_user.id})
        if sites:
            await service.save_keyword_ranks(sites[0].id, results, current_user.id, current_user.tenant_id)
    return {"rankings": results}


# ==================== SEO 数据查询 ====================


@router.get("/seo/rankings")
async def list_rankings(
    site_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("seo", "read")),
):
    """查看最新关键词排名。"""
    service = SiteService(session)
    if site_id is not None:
        if not await service.get_site(site_id, visible_user_ids(current_user)):
            raise HTTPException(status_code=404, detail="站点不存在")
        ranks = await service.list_keyword_ranks(site_id)
    else:
        sites = await service.list_sites(visible_user_ids(current_user))
        for s in sites:
            ranks = await service.list_keyword_ranks(s.id)
            if ranks:
                return [_rank_out(r) for r in ranks]
        ranks = []
    return [_rank_out(r) for r in ranks]


@router.get("/seo/contents")
async def list_seo_contents(
    site_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("seo", "read")),
):
    """查看已生成的 SEO 内容建议。"""
    service = SiteService(session)
    if site_id is not None:
        if not await service.get_site(site_id, visible_user_ids(current_user)):
            raise HTTPException(status_code=404, detail="站点不存在")
        contents = await service.list_seo_contents(site_id)
    else:
        contents = []
        sites = await service.list_sites(visible_user_ids(current_user))
        for s in sites:
            contents.extend(await service.list_seo_contents(s.id))
    return [_content_out(c) for c in contents]


class BulkCreateFromSEORequest(BaseModel):
    seo_content_ids: List[int] = Field(..., min_length=1)


@router.post("/sites/{site_id}/pages/bulk-from-seo", status_code=201)
async def bulk_create_pages_from_seo(
    site_id: int,
    request: BulkCreateFromSEORequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("page", "create")),
):
    """从 SEO 内容批量创建独立站页面。"""
    service = SiteService(session)
    if not await service.get_site(site_id, {current_user.id}):
        raise HTTPException(status_code=404, detail="站点不存在")
    result = await service.bulk_create_pages_from_seo(
        site_id, request.seo_content_ids, current_user.id, current_user.tenant_id,
    )
    return result