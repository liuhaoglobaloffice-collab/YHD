"""
P1-G5.4: 独立站 SEO 文件生成器（sitemap.xml / robots.txt / JSON-LD schema）。

覆盖：
- sitemap 只收录已发布页面（草稿不进 sitemap）
- robots.txt 指向 sitemap
- blog → Article / product → Product / page → WebPage 的 JSON-LD schema
- API 层：GET /sites/{id}/seo/files 与 GET /sites/{id}/pages/{id}/schema
- 全部输出标记 source_type=RULE_BASED（规则驱动，基于真实页面数据）
"""

import os
import uuid
from datetime import UTC, datetime

import pytest


# ==================== 测试数据构造 ====================


def _site():
    from src.site_os.models import SiteConfig

    return SiteConfig(id=1, domain="example.com", name="Test Store")


def _page(**kw):
    from src.site_os.models import SitePage, SitePageStatus

    defaults = dict(
        id=10,
        site_id=1,
        title="LED Guide",
        slug="blog/led-guide",
        content_type="blog",
        status=SitePageStatus.PUBLISHED,
        published_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 8, 20, tzinfo=UTC),
        meta_title="LED Buying Guide",
        meta_description="How to buy LED lights",
        keywords=["led", "manufacturer"],
    )
    defaults.update(kw)
    return SitePage(**defaults)


# ==================== 单元层：SEOFilesGenerator ====================


class TestSEOFilesGenerator:
    """规则驱动的 sitemap / robots / schema 生成。"""

    def test_sitemap_contains_published_pages_only(self):
        from src.site_os.seo_files import SEOFilesGenerator

        published = _page()
        draft = _page(id=11, slug="blog/draft-page", status="draft")
        xml = SEOFilesGenerator().generate_sitemap(_site(), [published, draft])

        assert xml.startswith("<?xml")
        assert "http://www.sitemaps.org/schemas/sitemap/0.9" in xml
        assert "https://example.com/" in xml  # 首页
        assert "https://example.com/blog/led-guide" in xml  # 已发布页面
        assert "blog/draft-page" not in xml  # 草稿不进 sitemap
        assert "<lastmod>2026-08-20</lastmod>" in xml

    def test_sitemap_escapes_urls(self):
        from src.site_os.seo_files import SEOFilesGenerator

        page = _page(slug='blog/a&b<c>')
        xml = SEOFilesGenerator().generate_sitemap(_site(), [page])
        assert "a&amp;b&lt;c" in xml

    def test_robots_txt_contains_sitemap_link(self):
        from src.site_os.seo_files import SEOFilesGenerator

        robots = SEOFilesGenerator().generate_robots(_site())

        assert "User-agent: *" in robots
        assert "Allow: /" in robots
        assert "Sitemap: https://example.com/sitemap.xml" in robots

    def test_blog_schema_is_article(self):
        from src.site_os.seo_files import SEOFilesGenerator

        schema = SEOFilesGenerator().generate_page_schema(_site(), _page())
        assert schema["@type"] == "Article"
        assert schema["headline"] == "LED Buying Guide"
        assert schema["keywords"] == "led, manufacturer"
        assert schema["mainEntityOfPage"] == "https://example.com/blog/led-guide"
        assert schema["author"]["@type"] == "Organization"
        assert schema["author"]["name"] == "Test Store"
        assert schema["datePublished"].startswith("2026-08-01")

    def test_product_schema_is_product(self):
        from src.site_os.seo_files import SEOFilesGenerator

        page = _page(content_type="product", slug="products/led-bulb")
        schema = SEOFilesGenerator().generate_page_schema(_site(), page)
        assert schema["@type"] == "Product"
        assert schema["name"] == "LED Buying Guide"
        assert schema["url"] == "https://example.com/products/led-bulb"

    def test_page_schema_is_webpage(self):
        from src.site_os.seo_files import SEOFilesGenerator

        page = _page(content_type="page", slug="about-us")
        schema = SEOFilesGenerator().generate_page_schema(_site(), page)
        assert schema["@type"] == "WebPage"
        assert schema["publisher"]["name"] == "Test Store"

    def test_json_ld_script_wrapper(self):
        from src.site_os.seo_files import SEOFilesGenerator

        gen = SEOFilesGenerator()
        schema = gen.generate_page_schema(_site(), _page())
        script = gen.to_json_ld_script(schema)
        assert script.startswith('<script type="application/ld+json">')
        assert script.endswith("</script>")
        assert "schema.org" in script


# ==================== API 层 ====================


@pytest.fixture
def api_env(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "seo_files_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


class TestSEOFilesAPI:
    """GET /site/sites/{id}/seo/files 与 /pages/{id}/schema。"""

    def _login_headers(self, client):
        suffix = uuid.uuid4().hex[:8]
        client.post(
            "/api/v1/auth/register",
            json={
                "username": f"sf_user_{suffix}",
                "email": f"sf_{suffix}@example.com",
                "full_name": "SEO Files User",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"username": f"sf_user_{suffix}", "password": "testpass123"},
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_seo_files_and_page_schema_endpoints(self, api_env):
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            site = client.post(
                "/api/v1/site/sites",
                json={"domain": "store.example.com", "name": "Store"},
                headers=headers,
            )
            assert site.status_code == 201, site.text
            site_id = site.json()["id"]

            published = client.post(
                f"/api/v1/site/sites/{site_id}/pages",
                json={
                    "title": "LED Guide",
                    "slug": "blog/led-guide",
                    "content_type": "blog",
                    "status": "published",
                    "meta_title": "LED Buying Guide",
                    "keywords": ["led", "manufacturer"],
                },
                headers=headers,
            )
            assert published.status_code == 201, published.text
            page_id = published.json()["id"]

            draft = client.post(
                f"/api/v1/site/sites/{site_id}/pages",
                json={"title": "Draft", "slug": "blog/draft-page", "status": "draft"},
                headers=headers,
            )
            assert draft.status_code == 201, draft.text

            # SEO 文件（sitemap + robots）
            files = client.get(
                f"/api/v1/site/sites/{site_id}/seo/files", headers=headers
            )
            assert files.status_code == 200, files.text
            data = files.json()
            assert data["source_type"] == "RULE_BASED"
            assert "https://store.example.com/blog/led-guide" in data["sitemap_xml"]
            assert "blog/draft-page" not in data["sitemap_xml"]
            assert "Sitemap: https://store.example.com/sitemap.xml" in data["robots_txt"]
            assert data["published_pages"] == 1

            # 页面 JSON-LD schema
            schema = client.get(
                f"/api/v1/site/sites/{site_id}/pages/{page_id}/schema",
                headers=headers,
            )
            assert schema.status_code == 200, schema.text
            sdata = schema.json()
            assert sdata["source_type"] == "RULE_BASED"
            assert sdata["schema"]["@type"] == "Article"
            assert "application/ld+json" in sdata["json_ld"]
            assert "schema.org" in sdata["json_ld"]

    def test_seo_files_site_not_found_404(self, api_env):
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            resp = client.get(
                "/api/v1/site/sites/999999/seo/files", headers=headers
            )
            assert resp.status_code == 404