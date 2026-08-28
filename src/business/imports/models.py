"""
S1 操作台资料导入 - 数据模型

提供资料导入任务记录（ImportRecord）以及
客户（Customer）/ 合同（Contract）/ 报价（Quotation）基础资料表，
供应商沿用 src/business/supplier 模块。
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


class ImportType(str, Enum):
    """资料导入类型"""

    SUPPLIER = "supplier"  # 供应商（复用供应商模块）
    CUSTOMER = "customer"  # 客户
    CONTRACT = "contract"  # 合同
    QUOTATION = "quotation"  # 报价


class ImportStatus(str, Enum):
    """导入任务状态"""

    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 全部成功
    PARTIAL = "partial"  # 部分成功
    FAILED = "failed"  # 失败


class ImportRecord(Base):
    """
    资料导入任务记录

    记录每次批量导入的元信息、统计结果与错误明细，
    用于操作台"导入历史"展示与审计追溯。
    """

    __tablename__ = "import_records"

    id = Column(Integer, primary_key=True, index=True, comment="导入记录ID")

    # 导入类型与文件
    import_type = Column(
        SQLEnum(ImportType), nullable=False, index=True, comment="导入类型"
    )
    filename = Column(String(500), nullable=False, comment="文件名")
    file_type = Column(String(20), nullable=False, default="excel", comment="文件类型")

    # 统计
    status = Column(
        SQLEnum(ImportStatus),
        nullable=False,
        default=ImportStatus.PROCESSING,
        index=True,
        comment="导入状态",
    )
    total = Column(Integer, nullable=False, default=0, comment="总条数")
    success = Column(Integer, nullable=False, default=0, comment="成功条数")
    failed = Column(Integer, nullable=False, default=0, comment="失败条数")
    errors = Column(JSON, nullable=True, comment="错误明细（JSON 数组）")

    # 归属
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="导入人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    __table_args__ = (
        Index("idx_import_records_created_by_type", "created_by", "import_type"),
    )

    def __repr__(self) -> str:
        return f"<ImportRecord(id={self.id}, type='{self.import_type}', status='{self.status}')>"


class Customer(Base):
    """客户基础资料表（S1 资料导入落库）"""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, comment="客户ID")

    # 基本信息
    name = Column(String(255), nullable=False, index=True, comment="客户/联系人名称")
    company = Column(String(255), nullable=True, index=True, comment="公司名称")
    country = Column(String(100), nullable=True, index=True, comment="国家")
    city = Column(String(100), nullable=True, comment="城市")
    address = Column(Text, nullable=True, comment="详细地址")

    # 联系方式
    phone = Column(String(50), nullable=True, comment="电话")
    email = Column(String(255), nullable=True, comment="邮箱")
    website = Column(String(500), nullable=True, comment="网站")
    wechat = Column(String(100), nullable=True, comment="微信号")
    whatsapp = Column(String(100), nullable=True, comment="WhatsApp")

    # 业务信息
    product_interest = Column(String(500), nullable=True, comment="感兴趣产品")
    status = Column(String(50), nullable=False, default="new", index=True, comment="客户状态")
    source = Column(String(100), nullable=True, comment="数据来源")
    notes = Column(Text, nullable=True, comment="备注")

    # 归属
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}')>"


class Contract(Base):
    """合同资料表（S1 资料导入落库）"""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True, comment="合同ID")

    # 合同信息
    contract_no = Column(String(100), nullable=False, index=True, comment="合同编号")
    name = Column(String(255), nullable=True, comment="合同名称")
    customer_name = Column(String(255), nullable=True, index=True, comment="客户名称")
    supplier_name = Column(String(255), nullable=True, comment="供应商名称")

    # 金额
    amount = Column(Float, nullable=True, comment="合同金额")
    currency = Column(String(10), nullable=True, default="USD", comment="币种")

    # 有效期
    start_date = Column(DateTime, nullable=True, comment="开始日期")
    end_date = Column(DateTime, nullable=True, comment="结束日期")

    status = Column(String(50), nullable=False, default="active", index=True, comment="合同状态")
    notes = Column(Text, nullable=True, comment="备注")

    # 归属
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, no='{self.contract_no}')>"


class Quotation(Base):
    """报价资料表（S1 资料导入落库）"""

    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True, comment="报价ID")

    # 报价信息
    quotation_no = Column(String(100), nullable=False, index=True, comment="报价编号")
    name = Column(String(255), nullable=True, comment="报价名称")
    customer_name = Column(String(255), nullable=True, index=True, comment="客户名称")

    # 产品与价格
    product = Column(String(255), nullable=True, comment="产品")
    unit_price = Column(Float, nullable=True, comment="单价")
    quantity = Column(Integer, nullable=True, comment="数量")
    amount = Column(Float, nullable=True, comment="总金额")
    currency = Column(String(10), nullable=True, default="USD", comment="币种")

    valid_until = Column(DateTime, nullable=True, comment="有效期至")
    status = Column(String(50), nullable=False, default="pending", index=True, comment="报价状态")
    notes = Column(Text, nullable=True, comment="备注")

    # 归属
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<Quotation(id={self.id}, no='{self.quotation_no}')>"
