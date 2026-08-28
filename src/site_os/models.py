"""
S4 独立站 + SEO - 数据模型

定义站点配置（SiteConfig）、独立站页面（SitePage）、
关键词排名（KeywordRank）、SEO 内容建议（SEOContent）的数据结构。
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)

from src.database.base import Base


class SitePageStatus(str, Enum):
    """页面状态"""

    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 已发布
    ARCHIVED = "archived"  # 已归档


class RankTrend(str, Enum):
    """排名趋势"""

    UP = "up"  # 上升
    DOWN = "down"  # 下降
    STABLE = "stable"  # 持平
    NEW = "new"  # 新收录


class SiteConfig(Base):
    """独立站配置"""

    __tablename__ = "site_configs"

    id = Column(Integer, primary_key=True, index=True, comment="配置ID")

    domain = Column(String(255), nullable=False, index=True, comment="站点域名")
    name = Column(String(255), nullable=False, comment="站点名称")
    platform = Column(String(50), nullable=False, default="shopify", comment="建站平台")
    status = Column(String(50), nullable=False, default="active", comment="状态")

    # SEO 基础
    default_meta_title = Column(String(500), nullable=True, comment="默认标题")
    default_meta_description = Column(Text, nullable=True, comment="默认描述")
    default_lang = Column(String(20), nullable=True, default="en", comment="默认语言")
    target_countries = Column(JSON, nullable=True, comment="目标国家")
    target_keywords = Column(JSON, nullable=True, comment="目标关键词")

    # 集成凭据（真实接入时用于建站平台 API）
    credentials = Column(JSON, nullable=True, comment="平台凭据")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<SiteConfig(id={self.id}, domain='{self.domain}')>"


class SitePage(Base):
    """独立站页面（内容发布）"""

    __tablename__ = "site_pages"

    id = Column(Integer, primary_key=True, index=True, comment="页面ID")

    site_id = Column(
        Integer, ForeignKey("site_configs.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 页面信息
    title = Column(String(500), nullable=False, comment="页面标题")
    slug = Column(String(255), nullable=False, index=True, comment="URL 别名")
    content = Column(Text, nullable=True, comment="正文内容（Markdown/HTML）")
    content_type = Column(String(50), nullable=False, default="page", comment="内容类型（page/blog/product）")

    # SEO 元数据
    meta_title = Column(String(500), nullable=True, comment="SEO 标题")
    meta_description = Column(Text, nullable=True, comment="SEO 描述")
    keywords = Column(JSON, nullable=True, comment="关键词")
    canonical_url = Column(String(1000), nullable=True, comment="规范 URL")

    # 状态
    status = Column(
        SQLEnum(SitePageStatus), nullable=False, default=SitePageStatus.DRAFT, index=True, comment="状态"
    )
    published_at = Column(DateTime(timezone=True), nullable=True, comment="发布时间")

    # 统计
    views = Column(Integer, nullable=False, default=0, comment="访问量")
    conversions = Column(Integer, nullable=False, default=0, comment="转化数")

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_site_pages_site_slug", "site_id", "slug"),
    )

    def __repr__(self) -> str:
        return f"<SitePage(id={self.id}, title='{self.title}', status='{self.status}')>"


class KeywordRank(Base):
    """关键词排名跟踪"""

    __tablename__ = "keyword_ranks"

    id = Column(Integer, primary_key=True, index=True, comment="记录ID")

    site_id = Column(
        Integer, ForeignKey("site_configs.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )
    keyword = Column(String(255), nullable=False, index=True, comment="关键词")
    country = Column(String(100), nullable=True, comment="目标国家")

    # 排名
    rank = Column(Integer, nullable=True, comment="当前排名（1-100，null=未进前100）")
    previous_rank = Column(Integer, nullable=True, comment="上次排名")
    trend = Column(
        SQLEnum(RankTrend), nullable=False, default=RankTrend.NEW, comment="排名趋势"
    )
    search_volume = Column(Integer, nullable=True, comment="月搜索量")
    url = Column(String(1000), nullable=True, comment="排名页面 URL")

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    checked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="检查时间")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )

    __table_args__ = (
        Index("idx_keyword_ranks_site_kw", "site_id", "keyword"),
    )

    def __repr__(self) -> str:
        return f"<KeywordRank(id={self.id}, keyword='{self.keyword}', rank={self.rank})>"


class SEOContent(Base):
    """SEO 内容建议（AI 生成）"""

    __tablename__ = "seo_contents"

    id = Column(Integer, primary_key=True, index=True, comment="建议ID")

    site_id = Column(
        Integer, ForeignKey("site_configs.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )
    keyword = Column(String(255), nullable=False, comment="目标关键词")

    # 内容建议
    title = Column(String(500), nullable=True, comment="推荐标题")
    meta_description = Column(Text, nullable=True, comment="推荐描述")
    outline = Column(JSON, nullable=True, comment="内容大纲（数组）")
    content = Column(Text, nullable=True, comment="生成的文章内容")
    content_type = Column(String(50), nullable=False, default="blog", comment="内容类型")

    # AI 亮点
    suggested_slug = Column(String(255), nullable=True, comment="推荐 URL")
    suggested_tags = Column(JSON, nullable=True, comment="推荐标签")
    search_intent = Column(String(100), nullable=True, comment="搜索意图")

    # 生成信息
    method = Column(String(20), nullable=False, default="ai", comment="生成方式（ai/mock）")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<SEOContent(id={self.id}, keyword='{self.keyword}')>"