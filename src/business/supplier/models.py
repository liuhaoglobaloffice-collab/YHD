"""
供应商情报系统 - 数据模型

定义供应商、联系人、证书和风险评估的数据结构。
"""

from datetime import UTC, datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from src.database.base import Base


# ============================================
# 枚举类型定义
# ============================================


class SupplierStatus(str, Enum):
    """供应商状态"""

    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 停用
    BLACKLIST = "blacklist"  # 黑名单
    PENDING = "pending"  # 待审核


class BusinessType(str, Enum):
    """企业类型"""

    MANUFACTURER = "manufacturer"  # 制造商
    TRADING = "trading"  # 贸易商
    AGENT = "agent"  # 代理商
    DISTRIBUTOR = "distributor"  # 分销商
    SERVICE = "service"  # 服务商


class RiskLevel(str, Enum):
    """风险等级"""

    VERY_LOW = "very_low"  # 很低风险
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 极高风险


class CertificateType(str, Enum):
    """证书类型"""

    ISO9001 = "iso_9001"  # ISO 9001 质量管理体系
    ISO14001 = "iso_14001"  # ISO 14001 环境管理体系
    CE = "ce"  # CE 认证
    FDA = "fda"  # FDA 认证
    ROHS = "rohs"  # RoHS 认证
    BUSINESS_LICENSE = "business_license"  # 营业执照
    EXPORT_LICENSE = "export_license"  # 出口许可证
    OTHER = "other"  # 其他证书


# ============================================
# 数据模型定义
# ============================================


class Supplier(Base):
    """
    供应商基础信息表

    存储供应商的核心信息，包括公司名称、地址、联系方式、
    业务类型、注册资本、信用评级等。
    """

    __tablename__ = "suppliers"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="供应商ID")

    # 基本信息
    name = Column(String(255), nullable=False, index=True, comment="供应商名称")
    legal_name = Column(String(255), nullable=True, comment="法定名称（全称）")
    code = Column(
        String(50), unique=True, nullable=True, index=True, comment="供应商编码"
    )

    # 地理位置
    country = Column(String(100), nullable=False, index=True, comment="国家")
    province = Column(String(100), nullable=True, comment="省份/州")
    city = Column(String(100), nullable=True, index=True, comment="城市")
    district = Column(String(100), nullable=True, comment="区/县")
    address = Column(Text, nullable=True, comment="详细地址")
    postal_code = Column(String(20), nullable=True, comment="邮政编码")

    # 业务信息
    business_type = Column(
        SQLEnum(BusinessType),
        nullable=False,
        default=BusinessType.MANUFACTURER,
        comment="企业类型",
    )
    product_category = Column(
        String(255), nullable=True, index=True, comment="主营产品类别"
    )
    industry = Column(String(100), nullable=True, index=True, comment="所属行业")

    # 企业规模
    established_date = Column(DateTime(timezone=True), nullable=True, comment="成立日期")
    registered_capital = Column(Float, nullable=True, comment="注册资本（USD）")
    employee_count = Column(Integer, nullable=True, comment="员工数量")
    annual_revenue = Column(Float, nullable=True, comment="年营业额（USD）")

    # 联系方式
    phone = Column(String(50), nullable=True, comment="公司电话")
    email = Column(String(255), nullable=True, comment="公司邮箱")
    website = Column(String(500), nullable=True, comment="公司网站")
    wechat = Column(String(100), nullable=True, comment="微信号")
    whatsapp = Column(String(100), nullable=True, comment="WhatsApp")

    # 信用与评级
    credit_rating = Column(
        String(10), nullable=True, comment="信用评级（AAA, AA, A, BBB, BB, B, C）"
    )
    risk_score = Column(Float, nullable=True, comment="综合风险评分 (0-100)")

    # 认证与资质
    has_iso9001 = Column(Boolean, default=False, comment="是否有 ISO 9001 认证")
    has_iso14001 = Column(Boolean, default=False, comment="是否有 ISO 14001 认证")
    has_export_license = Column(Boolean, default=False, comment="是否有出口许可证")

    # 合作信息
    cooperation_years = Column(Integer, nullable=True, comment="合作年限")
    total_orders = Column(Integer, default=0, comment="历史订单总数")
    total_amount = Column(Float, default=0.0, comment="历史交易总额（USD）")

    # 状态
    status = Column(
        SQLEnum(SupplierStatus),
        nullable=False,
        default=SupplierStatus.ACTIVE,
        index=True,
        comment="供应商状态",
    )
    is_verified = Column(Boolean, default=False, comment="是否已实地验厂")

    # 备注
    description = Column(Text, nullable=True, comment="供应商简介")
    notes = Column(Text, nullable=True, comment="内部备注")
    tags = Column(String(500), nullable=True, comment="标签（逗号分隔）")

    # 数据来源
    source = Column(
        String(100), nullable=True, comment="数据来源（alibaba, made-in-china, manual）"
    )
    source_url = Column(String(1000), nullable=True, comment="来源URL")

    # 时间戳
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
    last_contacted_at = Column(DateTime(timezone=True), nullable=True, comment="最后联系时间")

    # 创建人
    created_by = Column(Integer, nullable=True, comment="创建人ID")

    # 关系
    contacts = relationship(
        "SupplierContact", back_populates="supplier", cascade="all, delete-orphan"
    )
    certificates = relationship(
        "SupplierCertificate", back_populates="supplier", cascade="all, delete-orphan"
    )
    risk_assessments = relationship(
        "SupplierRiskAssessment",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', status='{self.status}')>"


class SupplierContact(Base):
    """
    供应商联系人表

    存储供应商的关键联系人信息，包括姓名、职位、联系方式等。
    一个供应商可以有多个联系人。
    """

    __tablename__ = "supplier_contacts"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="联系人ID")

    # 外键
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="供应商ID",
    )

    # 基本信息
    name = Column(String(100), nullable=False, comment="联系人姓名")
    name_en = Column(String(100), nullable=True, comment="英文姓名")
    position = Column(String(100), nullable=True, comment="职位")
    department = Column(String(100), nullable=True, comment="部门")

    # 联系方式
    phone = Column(String(50), nullable=True, comment="电话")
    mobile = Column(String(50), nullable=True, comment="手机")
    email = Column(String(255), nullable=True, comment="邮箱")
    wechat = Column(String(100), nullable=True, comment="微信号")
    whatsapp = Column(String(100), nullable=True, comment="WhatsApp")
    skype = Column(String(100), nullable=True, comment="Skype")

    # 标记
    is_primary = Column(Boolean, default=False, comment="是否主要联系人")
    is_decision_maker = Column(Boolean, default=False, comment="是否决策人")

    # 备注
    notes = Column(Text, nullable=True, comment="备注")

    # 时间戳
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
    last_contacted_at = Column(DateTime(timezone=True), nullable=True, comment="最后联系时间")

    # 关系
    supplier = relationship("Supplier", back_populates="contacts")

    def __repr__(self) -> str:
        return f"<SupplierContact(id={self.id}, name='{self.name}', supplier_id={self.supplier_id})>"


class SupplierCertificate(Base):
    """
    供应商资质证书表

    存储供应商的各类认证证书、资质文件信息，
    包括证书类型、编号、有效期等。
    """

    __tablename__ = "supplier_certificates"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="证书ID")

    # 外键
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="供应商ID",
    )

    # 证书信息
    certificate_type = Column(
        SQLEnum(CertificateType), nullable=False, index=True, comment="证书类型"
    )
    certificate_name = Column(String(255), nullable=False, comment="证书名称")
    certificate_number = Column(String(255), nullable=True, comment="证书编号")

    # 颁发机构
    issuing_authority = Column(String(255), nullable=True, comment="颁发机构")
    issuing_country = Column(String(100), nullable=True, comment="颁发国家")

    # 有效期
    issue_date = Column(DateTime(timezone=True), nullable=True, comment="颁发日期")
    expiry_date = Column(DateTime(timezone=True), nullable=True, comment="到期日期")
    is_permanent = Column(Boolean, default=False, comment="是否永久有效")

    # 文件
    file_url = Column(String(1000), nullable=True, comment="证书文件URL")
    file_name = Column(String(500), nullable=True, comment="文件名")

    # 验证状态
    is_verified = Column(Boolean, default=False, comment="是否已验证")
    verified_at = Column(DateTime(timezone=True), nullable=True, comment="验证时间")
    verified_by = Column(Integer, nullable=True, comment="验证人ID")

    # 备注
    notes = Column(Text, nullable=True, comment="备注")

    # 时间戳
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

    # 关系
    supplier = relationship("Supplier", back_populates="certificates")

    def __repr__(self) -> str:
        return f"<SupplierCertificate(id={self.id}, type='{self.certificate_type}', supplier_id={self.supplier_id})>"


class SupplierRiskAssessment(Base):
    """
    供应商风险评估表

    存储供应商的多维度风险评估结果，包括合规风险、
    财务风险、履约风险、质量风险，以及综合风险评级。
    """

    __tablename__ = "supplier_risk_assessments"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="评估ID")

    # 外键
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="供应商ID",
    )

    # 评估维度评分 (0-100分，分数越高风险越低)
    compliance_score = Column(
        Float, nullable=True, comment="合规评分 (法律、资质、认证)"
    )
    financial_score = Column(
        Float, nullable=True, comment="财务评分 (注册资本、营收、信用)"
    )
    delivery_score = Column(
        Float, nullable=True, comment="履约评分 (交货准时率、合同执行)"
    )
    quality_score = Column(
        Float, nullable=True, comment="质量评分 (产品质量、客户投诉)"
    )
    communication_score = Column(Float, nullable=True, comment="沟通评分 (响应速度、服务态度)")

    # 综合评分与等级
    overall_score = Column(Float, nullable=True, comment="综合评分 (0-100)")
    risk_level = Column(
        SQLEnum(RiskLevel),
        nullable=False,
        default=RiskLevel.MEDIUM,
        index=True,
        comment="风险等级",
    )

    # 评估结果
    strengths = Column(Text, nullable=True, comment="优势（JSON 数组）")
    weaknesses = Column(Text, nullable=True, comment="劣势（JSON 数组）")
    opportunities = Column(Text, nullable=True, comment="机会（JSON 数组）")
    threats = Column(Text, nullable=True, comment="威胁（JSON 数组）")

    # SWOT 总结
    swot_summary = Column(Text, nullable=True, comment="SWOT 分析总结")

    # AI 生成的风险报告
    risk_report = Column(Text, nullable=True, comment="风险评估报告（Markdown）")
    recommendations = Column(Text, nullable=True, comment="建议（JSON 数组）")

    # 评估信息
    assessment_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="评估日期"
    )
    assessor_id = Column(Integer, nullable=True, comment="评估人ID（用户或AI Agent）")
    assessment_method = Column(
        String(50),
        nullable=True,
        comment="评估方式（manual=人工, ai=AI自动, hybrid=混合）",
    )

    # 备注
    notes = Column(Text, nullable=True, comment="备注")

    # 时间戳
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

    # 关系
    supplier = relationship("Supplier", back_populates="risk_assessments")

    def __repr__(self) -> str:
        return f"<SupplierRiskAssessment(id={self.id}, supplier_id={self.supplier_id}, risk_level='{self.risk_level}')>"
