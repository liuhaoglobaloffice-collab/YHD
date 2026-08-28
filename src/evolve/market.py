"""
S5 AI 员工市场 - 市场服务

提供模板列表/添加员工/外部员工、技能包管理、员工技能安装。
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agents import AgentType
from src.evolve.models import EmployeeTemplate, SkillPack, TemplateCategory
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class MarketService:
    """AI 员工市场服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== 模板 ====================

    async def list_templates(
        self, category: Optional[str] = None, keyword: Optional[str] = None, page: int = 1, page_size: int = 50
    ) -> Dict[str, Any]:
        stmt = select(EmployeeTemplate)
        if category:
            stmt = stmt.where(EmployeeTemplate.category == TemplateCategory(category))
        if keyword:
            stmt = stmt.where(EmployeeTemplate.name.contains(keyword))
        total = len(list((await self.session.execute(stmt.with_only_columns(EmployeeTemplate.id))).scalars().all()))
        stmt = (
            stmt.order_by(EmployeeTemplate.installs.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return {"items": items, "total": total}

    async def get_template(self, template_id: int) -> Optional[EmployeeTemplate]:
        stmt = select(EmployeeTemplate).where(EmployeeTemplate.id == template_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_template(
        self, data: Dict[str, Any], created_by: Optional[int] = None
    ) -> EmployeeTemplate:
        tpl = EmployeeTemplate(
            name=data.get("name", ""),
            department=data.get("department", "operations"),
            position=data.get("position", "task_manager"),
            description=data.get("description"),
            agent_type=data.get("agent_type"),
            category=TemplateCategory(data.get("category", "internal")),
            author=data.get("author") or "system",
            version=data.get("version", "1.0"),
            price=data.get("price", 0),
            skill_ids=data.get("skill_ids"),
            system_prompt=data.get("system_prompt"),
            meta=data.get("meta"),
            created_by=created_by,
        )
        self.session.add(tpl)
        await self.session.commit()
        await self.session.refresh(tpl)
        return tpl

    async def install_template(
        self, template: EmployeeTemplate, owner_user_id: int, tenant_id: Optional[str] = None
    ) -> AIEmployee:
        """从模板安装创建 AI 员工（内部安装或外部添加）。"""
        registry = AIEmployeeRegistry(self.session)
        employee = AIEmployee(
            name=f"{template.name}",
            department=Department(template.department),
            position=Position(template.position),
            description=template.description or template.name,
            agent_type=AgentType(template.agent_type) if template.agent_type else None,
            status=AIEmployeeStatus.ACTIVE,
            metadata={
                "skills": await self._resolve_skills(template.skill_ids),
                "source_template": str(template.id),
                "market_category": template.category.value,
                "installed_from_market": True,
            },
        )
        registered = await registry.register(employee)
        # 安装量 +1
        template.installs += 1
        await self.session.commit()
        await self.session.refresh(template)
        return registered

    async def _resolve_skills(self, skill_ids: Optional[List[int]]) -> List[str]:
        if not skill_ids:
            return []
        stmt = select(SkillPack).where(SkillPack.id.in_(skill_ids))
        packs = list((await self.session.execute(stmt)).scalars().all())
        return [p.code for p in packs]

    # ==================== 技能包 ====================

    async def list_skill_packs(
        self, category: Optional[str] = None, keyword: Optional[str] = None
    ) -> List[SkillPack]:
        stmt = select(SkillPack).order_by(SkillPack.category.asc(), SkillPack.name.asc())
        items = list((await self.session.execute(stmt)).scalars().all())
        if category:
            items = [i for i in items if i.category == category]
        if keyword:
            items = [i for i in items if keyword.lower() in i.name.lower() or keyword.lower() in i.code.lower()]
        return items

    async def create_skill_pack(self, data: Dict[str, Any]) -> SkillPack:
        pack = SkillPack(
            name=data.get("name", ""),
            code=data.get("code", "").strip().lower().replace(" ", "-"),
            description=data.get("description"),
            category=data.get("category", "general"),
            capabilities=data.get("capabilities"),
            prompt_fragments=data.get("prompt_fragments"),
            tools=data.get("tools"),
            is_system=data.get("is_system", False),
            version=data.get("version", "1.0"),
        )
        self.session.add(pack)
        await self.session.commit()
        await self.session.refresh(pack)
        return pack

    async def install_skill(
        self, employee_id: int, skill: SkillPack, owner_user_id: int
    ) -> AIEmployee:
        """给 AI 员工安装技能。"""
        registry = AIEmployeeRegistry(self.session)
        try:
            employee = await registry.get(UUID(str(employee_id)))
        except Exception:  # noqa: BLE001
            raise ValueError("员工不存在")
        skills = list(employee.metadata.get("skills", []))
        if skill.code not in skills:
            skills.append(skill.code)
        employee.metadata["skills"] = skills
        updated = await registry.update(employee.id, employee)
        return updated

    async def seed_defaults(self) -> None:
        """系统启动：写入默认内部模板与技能包（幂等）。"""
        try:
            existing = (await self.session.execute(select(EmployeeTemplate).limit(1))).scalar_one_or_none()
            if existing:
                return

            skills_data = [
                {"name": "供应链分析", "code": "supply-chain-analysis", "category": "operations",
                 "description": "供应商风险/价格/产能多维分析能力",
                 "capabilities": ["供应商评估", "价格对比", "产能审核"]},
                {"name": "获客引擎", "code": "lead-generation", "category": "sales",
                 "description": "社媒/谷歌/海关三路线索挖掘",
                 "capabilities": ["线索挖掘", "客户画像", "跟进管理"]},
                {"name": "内容创作", "code": "content-creation", "category": "marketing",
                 "description": "SEO 文章与营销内容生成",
                 "capabilities": ["SEO 内容", "营销文案", "多语言翻译"]},
                {"name": "数据分析", "code": "data-analysis", "category": "analytics",
                 "description": "业务数据分析与可视化报告",
                 "capabilities": ["数据统计", "趋势预测", "报表生成"]},
                {"name": "客户服务", "code": "customer-service", "category": "sales",
                 "description": "多平台客户接待与售后",
                 "capabilities": ["WhatsApp 客服", "工单处理", "满意度分析"]},
                {"name": "市场调研", "code": "market-research", "category": "research",
                 "description": "竞品与行业动态调研",
                 "capabilities": ["竞品分析", "行业研究", "机会识别"]},
            ]
            pack_ids: Dict[int, int] = {}
            for s in skills_data:
                pack = SkillPack(
                    name=s["name"], code=s["code"], category=s["category"],
                    description=s["description"], capabilities=s["capabilities"],
                    is_system=True, version="1.0",
                )
                self.session.add(pack)
                await self.session.flush()
                pack_ids[s["code"]] = pack.id

            templates = [
                {"name": "鎏灏核心助理", "department": "ceo_office", "position": "ceo_assistant",
                 "description": "主账号专属 AI 助理，指挥鎏灏协调全局",
                 "agent_type": "gpt", "category": "internal", "installs": 128,
                 "skill_ids": [pack_ids["data-analysis"], pack_ids["supply-chain-analysis"]]},
                {"name": "金牌外贸销售", "department": "sales", "position": "sales_representative",
                 "description": "多平台获客 + 客户跟进 + 报价转化",
                 "agent_type": "grok", "category": "internal", "installs": 96,
                 "skill_ids": [pack_ids["lead-generation"], pack_ids["customer-service"]]},
                {"name": "内容增长官", "department": "marketing", "position": "content_writer",
                 "description": "SEO 内容创作 + 多语言发布",
                 "agent_type": "claude", "category": "internal", "installs": 74,
                 "skill_ids": [pack_ids["content-creation"], pack_ids["market-research"]]},
                {"name": "独立站优化师", "department": "marketing", "position": "seo_specialist",
                 "description": "独立站/SEO/排名优化专家",
                 "agent_type": "deepseek", "category": "internal", "installs": 61,
                 "skill_ids": [pack_ids["content-creation"], pack_ids["market-research"]]},
                # 外部模板（市场/第三方）
                {"name": "AI 谈判专家", "department": "sales", "position": "account_manager",
                 "description": "第三方市场：采购谈判与议价专家（付费模板）",
                 "agent_type": "gemini", "category": "external", "author": "LiuHao Market", "price": 99, "installs": 42,
                 "skill_ids": [pack_ids["supply-chain-analysis"], pack_ids["customer-service"]]},
                {"name": "跨境运营顾问", "department": "operations", "position": "operations_coordinator",
                 "description": "第三方市场：跨境电商运营全流程顾问（付费模板）",
                 "agent_type": "kimi", "category": "external", "author": "LiuHao Market", "price": 149, "installs": 35,
                 "skill_ids": [pack_ids["data-analysis"], pack_ids["market-research"]]},
            ]
            for t in templates:
                tpl = EmployeeTemplate(
                    name=t["name"], department=t["department"], position=t["position"],
                    description=t["description"], agent_type=t["agent_type"],
                    category=TemplateCategory(t["category"]),
                    author=t.get("author", "system"), version="1.0",
                    price=t.get("price", 0), rating=5, installs=t.get("installs", 0),
                    skill_ids=t["skill_ids"],
                    system_prompt=f"你是{t['name']}，负责{t['description']}。",
                )
                self.session.add(tpl)
            await self.session.commit()
            logger.info("market_defaults_seeded templates=%d skills=%d", len(templates), len(skills_data))
        except Exception as e:  # noqa: BLE001
            logger.warning("market_seed_skipped error=%s", str(e))