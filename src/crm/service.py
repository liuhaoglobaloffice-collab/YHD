"""
S3 自动获客 + 供应商分析 - CRM 服务

提供线索池管理（增删改查、状态流转）、跟进记录、
下次跟进提醒查询，以及获客结果入库。
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.models import (
    ActivityType,
    Lead,
    LeadActivity,
    LeadPriority,
    LeadSource,
    LeadStatus,
)

logger = logging.getLogger(__name__)


class LeadService:
    """线索（CRM）服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== 线索 CRUD ====================

    async def create_lead(
        self,
        data: Dict[str, Any],
        owner_user_id: int,
        tenant_id: Optional[str] = None,
    ) -> Lead:
        lead = Lead(
            source=LeadSource(data.get("source", "manual")),
            source_detail=data.get("source_detail"),
            source_type=data.get("source_type", "MOCK"),
            name=data.get("name", "").strip(),
            company=data.get("company"),
            country=data.get("country"),
            city=data.get("city"),
            industry=data.get("industry"),
            phone=data.get("phone"),
            email=data.get("email"),
            whatsapp=data.get("whatsapp"),
            wechat=data.get("wechat"),
            linkedin=data.get("linkedin"),
            website=data.get("website"),
            product_interest=data.get("product_interest"),
            estimated_value=data.get("estimated_value"),
            score=data.get("score", 50),
            status=LeadStatus(data.get("status", "new")),
            priority=LeadPriority(data.get("priority", "medium")),
            next_follow_up_at=data.get("next_follow_up_at"),
            notes=data.get("notes"),
            meta=data.get("meta"),
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
        )
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def create_leads_batch(
        self,
        items: List[Dict[str, Any]],
        owner_user_id: int,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """批量入库线索（去重：按 company+email 或 name）。"""
        created = 0
        skipped = 0
        for item in items:
            exists = await self._find_duplicate(
                name=item.get("name", "").strip(),
                company=item.get("company"),
                email=item.get("email"),
                owner_user_id=owner_user_id,
            )
            if exists:
                skipped += 1
                continue
            await self.create_lead(item, owner_user_id, tenant_id)
            created += 1
        return {"created": created, "skipped": skipped}

    async def _find_duplicate(
        self, name: str, company: Optional[str], email: Optional[str], owner_user_id: int
    ) -> bool:
        if not name and not email:
            return False
        stmt = select(Lead.id).where(Lead.owner_user_id == owner_user_id)
        result = await self.session.execute(stmt)
        ids = result.scalars().all()
        if not ids:
            return False
        for lead_id in ids:
            lead = (await self.session.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()
            if email and lead.email and lead.email.lower() == email.lower():
                return True
            if name and lead.name == name and company and lead.company == company:
                return True
        return False

    async def list_leads(
        self,
        user_ids: Set[int],
        status: Optional[str] = None,
        source: Optional[str] = None,
        keyword: Optional[str] = None,
        follow_up: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        stmt = select(Lead).where(Lead.owner_user_id.in_(list(user_ids)))
        if status:
            stmt = stmt.where(Lead.status == LeadStatus(status))
        if source:
            stmt = stmt.where(Lead.source == LeadSource(source))
        if keyword:
            like = f"%{keyword}%"
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    Lead.name.like(like),
                    Lead.company.like(like),
                    Lead.email.like(like),
                )
            )
        if follow_up:
            stmt = stmt.where(Lead.next_follow_up_at <= datetime.now(UTC))
        total_stmt = stmt
        total = len(
            list((await self.session.execute(total_stmt.with_only_columns(Lead.id))).scalars().all())
        )
        stmt = (
            stmt.order_by(Lead.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        leads = list((await self.session.execute(stmt)).scalars().all())
        return {"items": leads, "total": total, "page": page, "page_size": page_size}

    async def get_lead(self, lead_id: int, user_ids: Set[int]) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.owner_user_id.in_(list(user_ids)))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_lead(self, lead: Lead, data: Dict[str, Any]) -> Lead:
        for field in (
            "name",
            "company",
            "country",
            "city",
            "industry",
            "phone",
            "email",
            "whatsapp",
            "wechat",
            "linkedin",
            "website",
            "product_interest",
            "estimated_value",
            "score",
            "status",
            "priority",
            "next_follow_up_at",
            "notes",
            "quote_amount",
            "won_amount",
            "expected_close_at",
            "lost_reason",
        ):
            if field in data and data[field] is not None:
                if field in ("status", "priority"):
                    model_cls = LeadStatus if field == "status" else LeadPriority
                    setattr(lead, field, model_cls(data[field]))
                else:
                    setattr(lead, field, data[field])
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def delete_lead(self, lead_id: int, owner_user_id: int) -> bool:
        lead = await self.get_lead(lead_id, {owner_user_id})
        if not lead:
            return False
        await self.session.delete(lead)
        await self.session.commit()
        return True

    # ==================== 跟进 ====================

    async def add_activity(
        self,
        lead_id: int,
        owner_user_id: int,
        activity_type: str,
        content: str,
        result: Optional[str] = None,
        next_follow_up_at: Optional[datetime] = None,
    ) -> LeadActivity:
        lead = await self.get_lead(lead_id, {owner_user_id})
        if not lead:
            raise ValueError("线索不存在")
        activity = LeadActivity(
            lead_id=lead_id,
            activity_type=ActivityType(activity_type),
            content=content,
            result=result,
            created_by=owner_user_id,
        )
        self.session.add(activity)
        lead.last_activity_at = datetime.now(UTC)
        if next_follow_up_at is not None:
            lead.next_follow_up_at = next_follow_up_at
        await self.session.commit()
        await self.session.refresh(activity)
        return activity

    async def list_activities(self, lead_id: int) -> List[LeadActivity]:
        stmt = (
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead_id)
            .order_by(LeadActivity.created_at.desc())
            .limit(100)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ==================== 统计 ====================

    async def stats(self, user_ids: Set[int]) -> Dict[str, Any]:
        stmt = select(Lead).where(Lead.owner_user_id.in_(list(user_ids)))
        leads = list((await self.session.execute(stmt)).scalars().all())
        by_status: Dict[str, int] = {}
        by_source_type: Dict[str, int] = {}
        total_value = 0.0
        quote_total = 0.0
        won_total = 0.0
        lost_by_reason: Dict[str, int] = {}
        follow_up_due = 0
        now = datetime.now(UTC)
        STATUS_ORDER = ["new", "contacted", "qualified", "proposal", "won", "lost"]
        for lead in leads:
            key = lead.status.value
            by_status[key] = by_status.get(key, 0) + 1
            st = lead.source_type or "MOCK"
            by_source_type[st] = by_source_type.get(st, 0) + 1
            if lead.estimated_value:
                total_value += lead.estimated_value
            if lead.quote_amount:
                quote_total += lead.quote_amount
            if lead.won_amount:
                won_total += lead.won_amount
            if lead.lost_reason:
                reason = lead.lost_reason.strip()
                if reason:
                    lost_by_reason[reason] = lost_by_reason.get(reason, 0) + 1
            if lead.next_follow_up_at and lead.next_follow_up_at <= now:
                follow_up_due += 1
        total = len(leads)
        stages = [
            {
                "status": s,
                "count": by_status.get(s, 0),
                "rate": round((by_status.get(s, 0) / total) * 100, 1) if total else 0.0,
            }
            for s in STATUS_ORDER
        ]
        won = by_status.get("won", 0)
        return {
            "total": total,
            "by_status": by_status,
            "by_source_type": by_source_type,
            "stages": stages,
            "total_estimated_value": round(total_value, 2),
            "quote_total": round(quote_total, 2),
            "won_total": round(won_total, 2),
            "win_rate": round((won / total) * 100, 1) if total else 0.0,
            "lost_by_reason": dict(
                sorted(lost_by_reason.items(), key=lambda kv: kv[1], reverse=True)[:5]
            ),
            "follow_up_due": follow_up_due,
        }

    # ==================== 导出 ====================

    async def export_csv(self, user_ids: Set[int]) -> str:
        """导出线索为 CSV 字符串。"""
        import csv
        import io

        stmt = select(Lead).where(Lead.owner_user_id.in_(list(user_ids))).order_by(Lead.created_at.desc())
        leads = list((await self.session.execute(stmt)).scalars().all())
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "名称", "公司", "来源", "状态", "优先级", "国家", "行业",
                         "电话", "邮箱", "WhatsApp", "微信", "LinkedIn", "网站",
                         "产品兴趣", "预估价值", "评分", "下次跟进", "备注"])
        for l in leads:
            writer.writerow([
                l.id, l.name, l.company, l.source.value, l.status.value, l.priority.value,
                l.country, l.industry, l.phone, l.email, l.whatsapp, l.wechat,
                l.linkedin, l.website, l.product_interest, l.estimated_value,
                l.score, l.next_follow_up_at, l.notes,
            ])
        return output.getvalue()

    # ==================== AI 员工分配 ====================

    async def assign_to_employee(self, lead_id: int, employee_id: str, owner_user_id: int) -> Lead:
        """将线索分配给指定的 AI 员工。"""
        lead = await self.get_lead(lead_id, {owner_user_id})
        if not lead:
            raise ValueError("线索不存在")
        lead.assigned_employee_id = employee_id
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def batch_assign(self, lead_ids: List[int], employee_id: str, owner_user_id: int) -> int:
        """批量分配线索给 AI 员工。"""
        count = 0
        for lid in lead_ids:
            try:
                await self.assign_to_employee(lid, employee_id, owner_user_id)
                count += 1
            except ValueError:
                continue
        return count
