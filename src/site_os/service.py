"""
S4 独立站 + SEO - 独立站服务

提供站点配置管理、页面发布与管理、访问/转化统计。
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_os.models import (
    KeywordRank,
    RankTrend,
    SEOContent,
    SiteConfig,
    SitePage,
    SitePageStatus,
)

logger = logging.getLogger(__name__)


class SiteService:
    """独立站服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== 站点配置 ====================

    async def create_site(
        self,
        data: Dict[str, Any],
        owner_user_id: int,
        tenant_id: Optional[str] = None,
    ) -> SiteConfig:
        site = SiteConfig(
            domain=data.get("domain", "").strip(),
            name=data.get("name", "").strip() or data.get("domain", "My Store"),
            platform=data.get("platform", "shopify"),
            status=data.get("status", "active"),
            default_meta_title=data.get("default_meta_title"),
            default_meta_description=data.get("default_meta_description"),
            default_lang=data.get("default_lang", "en"),
            target_countries=data.get("target_countries"),
            target_keywords=data.get("target_keywords"),
            credentials=data.get("credentials"),
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
        )
        self.session.add(site)
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def list_sites(
        self,
        user_ids: Optional[Set[int]] = None,
        tenant_id: Optional[str] = None,
    ) -> List[SiteConfig]:
        """列出独立站。

        P1-G5.2 修复：user_ids=None 表示不过滤归属（OWNER 全租户可见），
        另可按 tenant_id 过滤；旧实现把 OWNER 的空可见集合当作"无归属用户"。
        """
        stmt = select(SiteConfig)
        if user_ids is not None:
            stmt = stmt.where(SiteConfig.owner_user_id.in_(list(user_ids)))
        if tenant_id:
            stmt = stmt.where(SiteConfig.tenant_id == tenant_id)
        stmt = stmt.order_by(SiteConfig.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_site(
        self,
        site_id: int,
        user_ids: Optional[Set[int]] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[SiteConfig]:
        stmt = select(SiteConfig).where(SiteConfig.id == site_id)
        if user_ids is not None:
            stmt = stmt.where(SiteConfig.owner_user_id.in_(list(user_ids)))
        if tenant_id:
            stmt = stmt.where(SiteConfig.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_site(self, site: SiteConfig, data: Dict[str, Any]) -> SiteConfig:
        for field in ("name", "domain", "platform", "status", "default_meta_title", "default_meta_description", "default_lang", "target_countries", "target_keywords", "credentials"):
            if field in data and data[field] is not None:
                setattr(site, field, data[field])
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def delete_site(self, site_id: int, owner_user_id: int) -> bool:
        site = await self.get_site(site_id, {owner_user_id})
        if not site:
            return False
        await self.session.delete(site)
        await self.session.commit()
        return True

    # ==================== 页面管理 ====================

    async def create_page(
        self,
        site_id: int,
        data: Dict[str, Any],
        owner_user_id: int,
        tenant_id: Optional[str] = None,
    ) -> SitePage:
        page = SitePage(
            site_id=site_id,
            title=data.get("title", "").strip(),
            slug=data.get("slug", "").strip() or self._slugify(data.get("title", "")),
            content=data.get("content"),
            content_type=data.get("content_type", "page"),
            meta_title=data.get("meta_title"),
            meta_description=data.get("meta_description"),
            keywords=data.get("keywords"),
            canonical_url=data.get("canonical_url"),
            status=SitePageStatus(data.get("status", "draft")),
            published_at=datetime.now(UTC) if data.get("status") == "published" else None,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
        )
        self.session.add(page)
        await self.session.commit()
        await self.session.refresh(page)
        return page

    @staticmethod
    def _slugify(text: str) -> str:
        slug = text.lower().replace(" ", "-").replace("/", "-")
        return "".join(c for c in slug if c.isalnum() or c == "-")[:80] or "page"

    async def list_pages(
        self, site_id: int, status: Optional[str] = None, page: int = 1, page_size: int = 50
    ) -> Dict[str, Any]:
        stmt = select(SitePage).where(SitePage.site_id == site_id)
        if status:
            stmt = stmt.where(SitePage.status == SitePageStatus(status))
        total = len(list((await self.session.execute(stmt.with_only_columns(SitePage.id))).scalars().all()))
        stmt = (
            stmt.order_by(SitePage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        pages = list((await self.session.execute(stmt)).scalars().all())
        return {"items": pages, "total": total}

    async def get_page(self, page_id: int) -> Optional[SitePage]:
        stmt = select(SitePage).where(SitePage.id == page_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_page(self, page: SitePage, data: Dict[str, Any]) -> SitePage:
        for field in ("title", "slug", "content", "content_type", "meta_title", "meta_description", "keywords", "canonical_url", "status"):
            if field in data and data[field] is not None:
                setattr(page, field, data[field])
        if data.get("status") == "published" and not page.published_at:
            page.published_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(page)
        return page

    async def publish_page(self, page: SitePage) -> SitePage:
        page.status = SitePageStatus.PUBLISHED
        if not page.published_at:
            page.published_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(page)
        return page

    async def delete_page(self, page_id: int) -> bool:
        page = await self.get_page(page_id)
        if not page:
            return False
        await self.session.delete(page)
        await self.session.commit()
        return True

    async def site_stats(self, site_id: int) -> Dict[str, Any]:
        """站点数据统计（访问量/转化）。"""
        pages = list(
            (await self.session.execute(select(SitePage).where(SitePage.site_id == site_id))).scalars().all()
        )
        total_views = sum(p.views for p in pages)
        total_conversions = sum(p.conversions for p in pages)
        published = sum(1 for p in pages if p.status == SitePageStatus.PUBLISHED)
        return {
            "pages": len(pages),
            "published": published,
            "total_views": total_views,
            "total_conversions": total_conversions,
            "conversion_rate": round(total_conversions / total_views * 100, 2) if total_views else 0.0,
        }

    # ==================== SEO 存储 ====================

    async def save_keyword_ranks(
        self, site_id: int, rankings: List[Dict[str, Any]], owner_user_id: Optional[int] = None, tenant_id: Optional[str] = None
    ) -> int:
        for item in rankings:
            rank = self.session.execute(
                select(KeywordRank)
                .where(KeywordRank.site_id == site_id, KeywordRank.keyword == item["keyword"])
                .order_by(KeywordRank.checked_at.desc())
            )
            last = (await rank).scalar_one_or_none()
            prev = last.rank if last else item.get("previous_rank")
            trend = "new"
            if item.get("rank") and prev and isinstance(prev, int):
                if int(item["rank"]) < prev:
                    trend = "up"
                elif int(item["rank"]) > prev:
                    trend = "down"
                else:
                    trend = "stable"
            self.session.add(
                KeywordRank(
                    site_id=site_id,
                    keyword=item["keyword"],
                    country=item.get("country"),
                    rank=item.get("rank"),
                    previous_rank=prev,
                    trend=RankTrend(trend),
                    search_volume=item.get("search_volume"),
                    url=item.get("url"),
                    owner_user_id=owner_user_id,
                    tenant_id=tenant_id,
                )
            )
        await self.session.commit()
        return len(rankings)

    async def list_keyword_ranks(self, site_id: int, limit: int = 100) -> List[KeywordRank]:
        """每个关键词返回最新一条排名。"""
        rows = {}  # keyword -> latest
        stmt = select(KeywordRank).where(KeywordRank.site_id == site_id).order_by(KeywordRank.checked_at.desc())
        all_rows = list((await self.session.execute(stmt)).scalars().all())
        for row in all_rows:
            if row.keyword not in rows:
                rows[row.keyword] = row
            if len(rows) >= limit:
                break
        return list(rows.values())

    async def save_seo_content(
        self, site_id: int, data: Dict[str, Any], created_by: Optional[int] = None, tenant_id: Optional[str] = None
    ) -> SEOContent:
        item = SEOContent(
            site_id=site_id,
            keyword=data.get("keyword", ""),
            title=data.get("title"),
            meta_description=data.get("meta_description"),
            outline=data.get("outline"),
            content=data.get("content"),
            content_type=data.get("content_type", "blog"),
            suggested_slug=data.get("suggested_slug"),
            suggested_tags=data.get("tags"),
            search_intent=data.get("search_intent"),
            # P1-G5.2: 优先持久化 source_type（LLM/RULE_BASED/NOT_CONFIGURED），旧数据为 ai/mock
            method=data.get("source_type") or data.get("method", "mock"),
            created_by=created_by,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def list_seo_contents(self, site_id: int, limit: int = 50) -> List[SEOContent]:
        stmt = (
            select(SEOContent)
            .where(SEOContent.site_id == site_id)
            .order_by(SEOContent.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def bulk_create_pages_from_seo(
        self, site_id: int, seo_content_ids: List[int], owner_user_id: int, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从 SEO 内容批量创建为独立站页面。"""
        stmt = select(SEOContent).where(
            SEOContent.id.in_(seo_content_ids),
            SEOContent.site_id == site_id,
        )
        contents = list((await self.session.execute(stmt)).scalars().all())
        created = 0
        skipped = 0
        for sc in contents:
            existing = (await self.session.execute(
                select(SitePage).where(SitePage.site_id == site_id, SitePage.slug == sc.suggested_slug)
            )).scalar_one_or_none()
            if existing:
                skipped += 1
                continue
            page = SitePage(
                site_id=site_id,
                title=sc.title or sc.keyword,
                slug=sc.suggested_slug or self._slugify(sc.keyword),
                content=sc.content,
                content_type=sc.content_type,
                meta_title=sc.title,
                meta_description=sc.meta_description,
                keywords=sc.suggested_tags,
                status=SitePageStatus.DRAFT,
                owner_user_id=owner_user_id,
                tenant_id=tenant_id,
            )
            self.session.add(page)
            created += 1
        if created:
            await self.session.commit()
        return {"created": created, "skipped": skipped, "total": len(contents)}