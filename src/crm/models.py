"""
S3 自动获客 + 供应商分析 - 数据模型

定义线索（Lead）、跟进记录（LeadActivity）、
海关数据（CustomsRecord）的数据结构。
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


class LeadSource(str, Enum):
    """线索来源"""

    SOCIAL = "social"  # 社媒（LinkedIn/Facebook 等）
    GOOGLE = "google"  # 谷歌搜索
    CUSTOMS = "customs"  # 海关数据
    MANUAL = "manual"  # 手动添加
    IMPORT = "import"  # 批量导入


class LeadStatus(str, Enum):
    """线索状态（销售漏斗）"""

    NEW = "new"  # 新线索
    CONTACTED = "contacted"  # 已联系
    QUALIFIED = "qualified"  # 已确认意向
    PROPOSAL = "proposal"  # 方案/报价中
    WON = "won"  # 成交
    LOST = "lost"  # 流失


class LeadPriority(str, Enum):
    """线索优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActivityType(str, Enum):
    """跟进活动类型"""

    CALL = "call"  # 电话
    EMAIL = "email"  # 邮件
    MESSAGE = "message"  # 平台消息
    MEETING = "meeting"  # 会议
    NOTE = "note"  # 备注


class Lead(Base):
    """客户线索（线索池）"""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, comment="线索ID")

    # 来源
    source = Column(SQLEnum(LeadSource), nullable=False, index=True, comment="线索来源")
    source_detail = Column(String(255), nullable=True, comment="来源详情（如平台/关键词）")
    source_type = Column(
        String(20), nullable=False, default="MOCK", index=True,
        comment="执行模式：REAL / MOCK / NOT_CONFIGURED",
    )

    # 基本信息
    name = Column(String(255), nullable=False, index=True, comment="客户/联系人名称")
    company = Column(String(255), nullable=True, index=True, comment="公司名称")
    country = Column(String(100), nullable=True, index=True, comment="国家")
    city = Column(String(100), nullable=True, comment="城市")
    industry = Column(String(100), nullable=True, comment="行业")

    # 联系方式
    phone = Column(String(50), nullable=True, comment="电话")
    email = Column(String(255), nullable=True, comment="邮箱")
    whatsapp = Column(String(100), nullable=True, comment="WhatsApp")
    wechat = Column(String(100), nullable=True, comment="微信")
    linkedin = Column(String(500), nullable=True, comment="LinkedIn")
    website = Column(String(500), nullable=True, comment="网站")

    # 业务
    product_interest = Column(String(500), nullable=True, comment="感兴趣产品")
    estimated_value = Column(Float, nullable=True, comment="预估订单价值（USD）")
    score = Column(Integer, nullable=False, default=50, comment="线索评分 0-100")

    # 询盘漏斗（V3）
    quote_amount = Column(Float, nullable=True, comment="报价金额（USD）")
    won_amount = Column(Float, nullable=True, comment="成交金额（USD）")
    expected_close_at = Column(DateTime(timezone=True), nullable=True, comment="预计成交时间")
    lost_reason = Column(String(500), nullable=True, comment="流失原因")

    # 状态与优先级
    status = Column(
        SQLEnum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True, comment="线索状态"
    )
    priority = Column(
        SQLEnum(LeadPriority), nullable=False, default=LeadPriority.MEDIUM, index=True, comment="优先级"
    )

    # 跟进
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True, index=True, comment="下次跟进时间")
    last_activity_at = Column(DateTime(timezone=True), nullable=True, comment="最近跟进时间")

    # 归属
    assigned_employee_id = Column(String(64), nullable=True, comment="负责 AI 员工ID")
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 备注
    notes = Column(Text, nullable=True, comment="备注")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 时间戳
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
        Index("idx_leads_owner_status", "owner_user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, name='{self.name}', status='{self.status}')>"


class LeadActivity(Base):
    """线索跟进记录"""

    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True, index=True, comment="活动ID")

    lead_id = Column(
        Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True, comment="线索ID"
    )
    activity_type = Column(SQLEnum(ActivityType), nullable=False, comment="活动类型")
    content = Column(Text, nullable=False, comment="活动内容")
    result = Column(String(500), nullable=True, comment="跟进结果")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<LeadActivity(id={self.id}, lead_id={self.lead_id}, type='{self.activity_type}')>"


class SupplierInquiry(Base):
    """供应商询价/比价记录（V3 三件套）"""

    __tablename__ = "supplier_inquiries"

    id = Column(Integer, primary_key=True, index=True, comment="询价ID")
    supplier_name = Column(String(255), nullable=False, index=True, comment="供应商名称")
    product = Column(String(255), nullable=False, index=True, comment="产品")
    quantity = Column(Integer, nullable=True, comment="数量")
    unit_price = Column(Float, nullable=True, comment="单价（USD）")
    currency = Column(String(10), default="USD", comment="币种")
    lead_time = Column(String(100), nullable=True, comment="交期（如 15 天）")
    payment = Column(String(100), nullable=True, comment="付款方式（T/T 30/70 等）")
    quality_note = Column(String(255), nullable=True, comment="质量/证书说明")
    note = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<SupplierInquiry(id={self.id}, supplier='{self.supplier_name}', product='{self.product}')>"


class CustomsRecord(Base):
    """海关进出口数据"""

    __tablename__ = "customs_records"

    id = Column(Integer, primary_key=True, index=True, comment="记录ID")

    # 商品
    hs_code = Column(String(20), nullable=True, index=True, comment="HS 编码")
    product = Column(String(255), nullable=False, index=True, comment="商品名称")
    product_desc = Column(Text, nullable=True, comment="商品描述")

    # 进出口
    importer_name = Column(String(255), nullable=True, index=True, comment="进口商")
    importer_country = Column(String(100), nullable=True, index=True, comment="进口国")
    exporter_name = Column(String(255), nullable=True, index=True, comment="出口商")
    exporter_country = Column(String(100), nullable=True, index=True, comment="出口国")

    # 数量与金额
    quantity = Column(Float, nullable=True, comment="数量")
    unit = Column(String(20), nullable=True, comment="单位")
    value = Column(Float, nullable=True, comment="金额（USD）")
    trade_date = Column(DateTime(timezone=True), nullable=True, index=True, comment="贸易日期")

    # 来源与归属
    source = Column(String(100), nullable=True, comment="数据来源")
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    __table_args__ = (
        Index("idx_customs_records_importer", "importer_name"),
    )

    def __repr__(self) -> str:
        return f"<CustomsRecord(id={self.id}, product='{self.product}')>"


class SupplierAnalysisReport(Base):
    """供应商分析报告（风险 / 价格 / 产能）"""

    __tablename__ = "supplier_analysis_reports"

    id = Column(Integer, primary_key=True, index=True, comment="报告ID")

    # 供应商
    supplier_id = Column(Integer, nullable=True, index=True, comment="供应商ID")
    supplier_name = Column(String(255), nullable=False, comment="供应商名称")
    product_category = Column(String(255), nullable=True, comment="产品类别")

    # 风险分析
    risk_level = Column(String(50), nullable=True, comment="风险等级")
    risk_score = Column(Float, nullable=True, comment="风险评分 0-100")
    risk_summary = Column(Text, nullable=True, comment="风险分析摘要")

    # 价格分析
    price_level = Column(String(50), nullable=True, comment="价格水平")
    price_score = Column(Float, nullable=True, comment="价格竞争力评分")
    price_summary = Column(Text, nullable=True, comment="价格分析摘要")

    # 产能分析
    capacity_level = Column(String(50), nullable=True, comment="产能水平")
    capacity_score = Column(Float, nullable=True, comment="产能评分")
    capacity_summary = Column(Text, nullable=True, comment="产能分析摘要")

    # 综合
    overall_score = Column(Float, nullable=True, comment="综合评分")
    overall_level = Column(String(50), nullable=True, comment="综合评级")
    report = Column(Text, nullable=True, comment="完整报告（Markdown）")
    recommendations = Column(JSON, nullable=True, comment="建议（JSON 数组）")

    # 生成信息
    analysis_method = Column(
        String(50), nullable=False, default="ai", comment="分析方式（ai/mock/hybrid）"
    )
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<SupplierAnalysisReport(id={self.id}, supplier='{self.supplier_name}')>"
