"""
S6 回归冒烟测试.

覆盖 S1-S5 关键回归点：
- 路由注册（accounts/imports/platforms/crm/site/market/system）
- RBAC：USER 角色核心权限
- 敏感数据脱敏工具
- 新模型均已在 Base.metadata 注册
"""

import pytest

from src.core.masking import mask_dict, mask_email, mask_phone, redact_secrets


class TestRouteRegistration:
    """S1-S5 关键端点路由注册"""

    @pytest.fixture(scope="class")
    def app_routes(self):
        from src.api.app import create_app

        app = create_app()

        def walk(router):
            paths = set()
            for r in getattr(router, "routes", []):
                if type(r).__name__ == "_IncludedRouter":
                    paths |= walk(getattr(r, "original_router", None))
                else:
                    p = getattr(r, "path", None)
                    if p:
                        paths.add(p)
            return paths

        return walk(app)

    @pytest.mark.parametrize(
        "path",
        [
            "/accounts/sub-accounts",  # S1 子账号
            "/imports/upload",  # S1 导入
            "/platforms/accounts",  # S2 多平台
            "/platforms/translate",  # S2 翻译
            "/crm/acquisition/run",  # S3 获客
            "/crm/suppliers/analyze",  # S3 供应商分析
            "/site/sites",  # S4 独立站
            "/site/seo/rankings/track",  # S4 SEO
            "/market/templates/install",  # S5 市场
            "/market/meta-learning/run",  # S5 元学习
            "/market/evolution/generate",  # S5 自我进化
            "/system/overview",  # S6 总览
            "/products",  # P3c 产品目录
        ],
    )
    def test_critical_routes_registered(self, app_routes, path):
        assert path in app_routes


class TestRBAC:
    """USER 角色的关键权限（验收依赖主账号可操作）"""

    def test_user_permissions(self):
        from src.identity.models import RoleEnum, User
        from src.identity.rbac import Permission, has_permission

        user = User(
            id=1,
            username="t",
            email="t@t.com",
            hashed_password="x",
            role=RoleEnum.USER,
            is_active=True,
            is_superuser=False,
        )
        for perm in [
            Permission.LEAD_CREATE,
            Permission.LEAD_READ,
            Permission.SITE_CREATE,
            Permission.SITE_READ,
            Permission.SEO_READ,
            Permission.EMPLOYEE_CREATE,
            Permission.EMPLOYEE_UPDATE,
            Permission.PLATFORM_CREATE,
            Permission.PLATFORM_MESSAGE_SEND,
            Permission.IMPORT_CREATE,
            Permission.SYSTEM_READ,
        ]:
            assert has_permission(user, perm), f"USER 缺少 {perm.value}"

    def test_viewer_is_readonly(self):
        from src.identity.models import RoleEnum, User
        from src.identity.rbac import Permission, has_permission

        viewer = User(
            id=2,
            username="v",
            email="v@t.com",
            hashed_password="x",
            role=RoleEnum.VIEWER,
            is_active=True,
            is_superuser=False,
        )
        assert has_permission(viewer, Permission.LEAD_READ)
        assert not has_permission(viewer, Permission.LEAD_CREATE)
        assert not has_permission(viewer, Permission.PLATFORM_CREATE)


class TestMasking:
    """敏感数据脱敏"""

    def test_mask_email(self):
        assert mask_email("john@example.com") == "jo***@example.com"
        assert mask_email("a@b.com") == "a***@b.com"
        assert mask_email(None) is None

    def test_mask_phone(self):
        masked = mask_phone("+86 138 0000 1234")
        assert masked is not None
        assert masked.endswith("1234")
        assert "***" in masked

    def test_mask_dict(self):
        data = mask_dict({"email": "a@b.com", "phone": "13800001234", "name": "Alice"})
        assert "***" in data["email"]
        assert "***" in data["phone"]
        assert data["name"] == "Alice"  # name 默认不脱敏

    def test_redact_secrets(self):
        data = redact_secrets({"credentials": {"token": "secret123"}, "name": "ok"})
        assert data["credentials"] == "***"  # 凭据整体打码
        assert data["name"] == "ok"


class TestModelsRegistered:
    """S1-S5 新模型均已注册到 Base.metadata"""

    @pytest.mark.parametrize(
        "table",
        [
            "import_records",  # S1
            "customers",
            "platform_accounts",  # S2
            "platform_messages",
            "leads",  # S3
            "customs_records",
            "supplier_analysis_reports",
            "site_configs",  # S4
            "site_pages",
            "keyword_ranks",
            "employee_templates",  # S5
            "skill_packs",
            "meta_knowledge",
            "evolution_proposals",
            "products",  # P3c 产品目录
        ],
    )
    def test_table_registered(self, table):
        from src.database.base import Base

        assert table in Base.metadata.tables, f"表 {table} 未注册"