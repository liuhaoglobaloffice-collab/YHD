"""
外贸报价单管理

提供报价单的创建、审核、发送、状态流转功能。
报价单关联 CRM 线索，支持通过平台消息发送。
"""

import structlog
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base

logger = structlog.get_logger(__name__)


# ==================== 数据模型 ====================


class QuoteStatus(str, Enum):
    """报价单状态"""
    DRAFT = "draft"           # 草稿
    PENDING_APPROVAL = "pending_approval"  # 待审批
    APPROVED = "approved"      # 已审批
    SENT = "sent"              # 已发送客户
    FOLLOWING_UP = "following_up"  # 跟进中
    ACCEPTED = "accepted"      # 客户已接受
    REJECTED = "rejected"      # 客户已拒绝
    EXPIRED = "expired"        # 已过期


class QuoteItem(Base):
    """报价单项"""
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="产品名称")
    product_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="产品编号")
    specification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="规格型号")
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="件", comment="单位")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="数量")
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, comment="单价（USD）")
    total_price: Mapped[float] = mapped_column(Float, nullable=False, comment="小计（USD）")
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class Quote(Base):
    """报价单"""
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True, comment="报价单号")

    # 关联线索
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("leads.id"), nullable=True, index=True, comment="关联线索")
    lead_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户名称")
    lead_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="客户公司")
    lead_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="客户邮箱")
    lead_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="客户电话")

    # 报价信息
    status: Mapped[QuoteStatus] = mapped_column(SAEnum(QuoteStatus), nullable=False, default=QuoteStatus.DRAFT, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False, comment="报价主题")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD", comment="币种")
    exchange_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, comment="汇率")
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="合计金额")
    discount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="折扣")
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="税率(%)")
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="税额")
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="总金额")
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, comment="有效期（天）")
    payment_terms: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="付款条件")
    delivery_terms: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="交货条款")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")

    # 审计
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    sent_at = Column(DateTime(timezone=True), nullable=True, comment="发送时间")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="过期时间")


# ==================== 服务层 ====================


class QuoteService:
    """报价单管理服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_quote(
        self,
        data: Dict[str, Any],
        owner_user_id: int,
        created_by: int,
        tenant_id: Optional[str] = None,
    ) -> Quote:
        """创建报价单。"""
        # 生成报价单号
        quote_number = await self._generate_quote_number()

        items_data = data.pop("items", [])

        # 计算金额
        subtotal = sum(
            item.get("quantity", 1) * item.get("unit_price", 0)
            for item in items_data
        )
        discount = data.get("discount", 0.0)
        tax_rate = data.get("tax_rate", 0.0)
        taxable = subtotal - discount
        tax_amount = taxable * tax_rate / 100
        total_amount = taxable + tax_amount

        valid_days = data.get("valid_days", 30)
        now = datetime.now(UTC)

        quote = Quote(
            quote_number=quote_number,
            lead_id=data.get("lead_id"),
            lead_name=data.get("lead_name", ""),
            lead_company=data.get("lead_company"),
            lead_email=data.get("lead_email"),
            lead_phone=data.get("lead_phone"),
            status=QuoteStatus.DRAFT,
            subject=data.get("subject", ""),
            currency=data.get("currency", "USD"),
            exchange_rate=data.get("exchange_rate", 1.0),
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            tax_rate=tax_rate,
            tax_amount=round(tax_amount, 2),
            total_amount=round(total_amount, 2),
            valid_days=valid_days,
            payment_terms=data.get("payment_terms"),
            delivery_terms=data.get("delivery_terms"),
            notes=data.get("notes"),
            created_by=created_by,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
            expires_at=now + timedelta(days=valid_days),
        )
        self.session.add(quote)
        await self.session.flush()

        # 创建报价单项
        for item_data in items_data:
            qty = item_data.get("quantity", 1)
            price = item_data.get("unit_price", 0)
            item = QuoteItem(
                quote_id=quote.id,
                product_name=item_data.get("product_name", ""),
                product_code=item_data.get("product_code"),
                specification=item_data.get("specification"),
                unit=item_data.get("unit", "件"),
                quantity=qty,
                unit_price=price,
                total_price=round(qty * price, 2),
                remark=item_data.get("remark"),
            )
            self.session.add(item)

        await self.session.commit()
        await self.session.refresh(quote)

        # 更新线索报价金额
        if quote.lead_id:
            from src.crm.models import Lead
            stmt = select(Lead).where(Lead.id == quote.lead_id)
            lead = (await self.session.execute(stmt)).scalar_one_or_none()
            if lead:
                lead.quote_amount = (lead.quote_amount or 0) + total_amount
                await self.session.commit()

        logger.info("quote_created", quote_id=quote.id, number=quote_number)
        return quote

    async def list_quotes(
        self,
        user_ids: Set[int],
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """列出报价单。"""
        query = select(Quote).where(Quote.owner_user_id.in_(list(user_ids)))

        if status:
            query = query.where(Quote.status == QuoteStatus(status))
        if keyword:
            like = f"%{keyword}%"
            from sqlalchemy import or_
            query = query.where(
                or_(
                    Quote.quote_number.like(like),
                    Quote.lead_name.like(like),
                    Quote.subject.like(like),
                )
            )

        total = len(list((await self.session.execute(query.with_only_columns(Quote.id))).scalars().all()))
        query = query.order_by(Quote.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        quotes = list((await self.session.execute(query)).scalars().all())

        return {"items": [await self._serialize(q) for q in quotes], "total": total, "page": page, "page_size": page_size}

    async def get_quote(self, quote_id: int, user_ids: Set[int]) -> Optional[Dict[str, Any]]:
        """获取报价单详情。"""
        stmt = select(Quote).where(Quote.id == quote_id, Quote.owner_user_id.in_(list(user_ids)))
        quote = (await self.session.execute(stmt)).scalar_one_or_none()
        if not quote:
            return None
        return await self._serialize(quote)

    async def update_quote_status(
        self, quote_id: int, owner_user_id: int, status: str
    ) -> Quote:
        """更新报价单状态。"""
        stmt = select(Quote).where(Quote.id == quote_id, Quote.owner_user_id == owner_user_id)
        quote = (await self.session.execute(stmt)).scalar_one_or_none()
        if not quote:
            raise ValueError("报价单不存在")

        new_status = QuoteStatus(status)
        quote.status = new_status

        if new_status == QuoteStatus.SENT:
            quote.sent_at = datetime.now(UTC)
        elif new_status == QuoteStatus.ACCEPTED:
            # 更新线索成交金额
            if quote.lead_id:
                from src.crm.models import Lead
                stmt = select(Lead).where(Lead.id == quote.lead_id)
                lead = (await self.session.execute(stmt)).scalar_one_or_none()
                if lead:
                    lead.won_amount = (lead.won_amount or 0) + quote.total_amount
                    from src.crm.models import LeadStatus
                    lead.status = LeadStatus.WON
                    await self.session.commit()

        await self.session.commit()
        await self.session.refresh(quote)
        return quote

    async def send_quote(
        self, quote_id: int, owner_user_id: int, send_via: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送报价单给客户。"""
        stmt = select(Quote).where(Quote.id == quote_id, Quote.owner_user_id == owner_user_id)
        quote = (await self.session.execute(stmt)).scalar_one_or_none()
        if not quote:
            raise ValueError("报价单不存在")

        # 通过平台消息发送
        sent_via = []
        if send_via == "whatsapp" and quote.lead_phone:
            from src.integrations.models import PlatformAccount, PlatformType
            from src.integrations.service import PlatformService

            stmt = (
                select(PlatformAccount)
                .where(
                    PlatformAccount.owner_user_id == owner_user_id,
                    PlatformAccount.platform == PlatformType.WHATSAPP,
                    PlatformAccount.is_active == True,
                )
                .limit(1)
            )
            wa = (await self.session.execute(stmt)).scalar_one_or_none()
            if wa:
                svc = PlatformService(self.session)
                await svc.send_message(
                    account_id=wa.id,
                    owner_user_id=owner_user_id,
                    to_id=quote.lead_phone,
                    content=f"Dear {quote.lead_name},\n\n"
                            f"Quotation {quote.quote_number}: {quote.subject}\n"
                            f"Total Amount: {quote.currency} {quote.total_amount:,.2f}\n"
                            f"Valid until: {quote.expires_at.strftime('%Y-%m-%d') if quote.expires_at else 'N/A'}\n\n"
                            f"Please let us know if you have any questions.\n\n"
                            f"Best regards",
                    to_name=quote.lead_name,
                )
                sent_via.append("whatsapp")

        # 更新状态
        quote.status = QuoteStatus.SENT
        quote.sent_at = datetime.now(UTC)
        await self.session.commit()

        # 记录活动
        if quote.lead_id:
            from src.crm.service import LeadService
            lead_svc = LeadService(self.session)
            await lead_svc.add_activity(
                lead_id=quote.lead_id,
                owner_user_id=owner_user_id,
                activity_type="note",
                content=f"报价单 {quote.quote_number} 已发送 ({', '.join(sent_via) if sent_via else '手动'})",
                result=f"金额: {quote.currency} {quote.total_amount:,.2f}",
            )

        return {"status": "sent", "sent_via": sent_via, "quote_number": quote.quote_number}

    async def _generate_quote_number(self) -> str:
        """生成唯一报价单号。"""
        now = datetime.now(UTC)
        prefix = f"QT-{now.strftime('%Y%m')}-"
        stmt = select(Quote.quote_number).where(Quote.quote_number.like(f"{prefix}%")).order_by(Quote.id.desc()).limit(1)
        last = (await self.session.execute(stmt)).scalar_one_or_none()
        seq = 1
        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f"{prefix}{seq:04d}"

    async def _serialize(self, quote: Quote) -> Dict[str, Any]:
        """序列化报价单。"""
        # 获取报价单项
        stmt = select(QuoteItem).where(QuoteItem.quote_id == quote.id).order_by(QuoteItem.id)
        items = list((await self.session.execute(stmt)).scalars().all())
        return {
            "id": quote.id,
            "quote_number": quote.quote_number,
            "lead_id": quote.lead_id,
            "lead_name": quote.lead_name,
            "lead_company": quote.lead_company,
            "lead_email": quote.lead_email,
            "lead_phone": quote.lead_phone,
            "status": quote.status.value,
            "subject": quote.subject,
            "currency": quote.currency,
            "subtotal": quote.subtotal,
            "discount": quote.discount,
            "tax_rate": quote.tax_rate,
            "tax_amount": quote.tax_amount,
            "total_amount": quote.total_amount,
            "valid_days": quote.valid_days,
            "payment_terms": quote.payment_terms,
            "delivery_terms": quote.delivery_terms,
            "notes": quote.notes,
            "items": [
                {
                    "id": item.id,
                    "product_name": item.product_name,
                    "product_code": item.product_code,
                    "specification": item.specification,
                    "unit": item.unit,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "remark": item.remark,
                }
                for item in items
            ],
            "created_at": quote.created_at.isoformat() if quote.created_at else None,
            "updated_at": quote.updated_at.isoformat() if quote.updated_at else None,
            "sent_at": quote.sent_at.isoformat() if quote.sent_at else None,
            "expires_at": quote.expires_at.isoformat() if quote.expires_at else None,
        }