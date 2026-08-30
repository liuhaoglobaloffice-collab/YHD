"""
P1-G5.4: 独立站 SEO 文件生成器（sitemap.xml / robots.txt / JSON-LD schema）。

规则驱动（source_type=RULE_BASED），基于真实已发布页面数据生成：
- sitemap.xml：仅收录 published 页面（草稿/归档不进 sitemap）
- robots.txt：声明抓取规则并指向 sitemap.xml
- JSON-LD schema：blog -> Article / product -> Product / 其他 -> WebPage
"""

import json
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from src.site_os.models import SiteConfig, SitePage, SitePageStatus
from src.site_os.seo import SOURCE_RULE_BASED

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SCHEMA_CONTEXT = "https://schema.org"


class SEOFilesGenerator:
    """规则驱动的 sitemap / robots / JSON-LD 生成器。"""

    # ==================== 基础工具 ====================

    def _base_url(self, site: SiteConfig) -> str:
        domain = (site.domain or "").strip()
        if not domain:
            return ""
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"
        return domain.rstrip("/")

    def _page_url(self, site: SiteConfig, page: SitePage) -> str:
        if page.canonical_url:
            return page.canonical_url
        base = self._base_url(site)
        slug = (page.slug or "").strip("/")
        if not slug:
            return f"{base}/"
        return f"{base}/{slug}"

    @staticmethod
    def _is_published(page: SitePage) -> bool:
        status = getattr(page, "status", None)
        status_value = getattr(status, "value", status)
        return status_value == SitePageStatus.PUBLISHED.value

    @staticmethod
    def _date_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        return value.date().isoformat()

    @staticmethod
    def _title_of(page: SitePage) -> str:
        return (page.meta_title or page.title or "").strip()

    # ==================== sitemap.xml ====================

    def generate_sitemap(self, site: SiteConfig, pages: List[SitePage]) -> str:
        """生成 sitemap.xml（仅已发布页面 + 首页）。"""
        base = self._base_url(site)
        entries: List[Dict[str, Optional[str]]] = [{"loc": f"{base}/"}]

        for page in pages:
            if not self._is_published(page):
                continue
            lastmod = self._date_str(
                page.updated_at or page.published_at or page.created_at
            )
            entries.append({"loc": self._page_url(site, page), "lastmod": lastmod})

        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append(f'<urlset xmlns="{SITEMAP_NS}">')
        for entry in entries:
            lines.append("<url>")
            lines.append(f"<loc>{escape(entry['loc'])}</loc>")
            if entry.get("lastmod"):
                lines.append(f"<lastmod>{entry['lastmod']}</lastmod>")
            lines.append("</url>")
        lines.append("</urlset>")
        return "\n".join(lines)

    # ==================== robots.txt ====================

    def generate_robots(self, site: SiteConfig) -> str:
        """生成 robots.txt（允许抓取 + 指向 sitemap）。"""
        base = self._base_url(site)
        return (
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            f"Sitemap: {base}/sitemap.xml\n"
        )

    # ==================== JSON-LD schema ====================

    def generate_page_schema(self, site: SiteConfig, page: SitePage) -> Dict[str, Any]:
        """生成页面 JSON-LD 结构化数据（blog->Article / product->Product / 其他->WebPage）。"""
        url = self._page_url(site, page)
        title = self._title_of(page)
        description = (page.meta_description or "").strip() or None
        keywords = page.keywords or []
        content_type = (page.content_type or "page").lower()
        organization = {"@type": "Organization", "name": site.name}
        date_published = page.published_at.isoformat() if page.published_at else None
        date_modified = page.updated_at.isoformat() if page.updated_at else None

        schema: Dict[str, Any] = {"@context": SCHEMA_CONTEXT}
        if content_type == "blog":
            schema["@type"] = "Article"
            schema["headline"] = title
            schema["mainEntityOfPage"] = url
            schema["author"] = organization
            if date_published:
                schema["datePublished"] = date_published
            if date_modified:
                schema["dateModified"] = date_modified
        elif content_type == "product":
            schema["@type"] = "Product"
            schema["name"] = title
            schema["url"] = url
            schema["publisher"] = organization
            if date_published:
                schema["datePublished"] = date_published
        else:
            schema["@type"] = "WebPage"
            schema["name"] = title
            schema["url"] = url
            schema["publisher"] = organization

        if description:
            schema["description"] = description
        if keywords:
            schema["keywords"] = ", ".join(str(k) for k in keywords)
        return schema

    def to_json_ld_script(self, schema: Dict[str, Any]) -> str:
        """包装为可直接嵌入页面的 <script type="application/ld+json">。"""
        payload = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        return f'<script type="application/ld+json">{payload}</script>'

    # ==================== 汇总输出 ====================

    def generate_files(self, site: SiteConfig, pages: List[SitePage]) -> Dict[str, Any]:
        """生成站点级 SEO 文件（sitemap + robots），供 API 返回。"""
        published = [p for p in pages if self._is_published(p)]
        return {
            "source_type": SOURCE_RULE_BASED,
            "sitemap_xml": self.generate_sitemap(site, published),
            "robots_txt": self.generate_robots(site),
            "published_pages": len(published),
            "sitemap_url": f"{self._base_url(site)}/sitemap.xml",
        }
