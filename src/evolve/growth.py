"""
S5 元学习 + 自我进化 - 鎏灏成长引擎

- 元学习：读取系统内 AI 员工信息（部门/职位/技能），鎏灏吸收为自身知识
- 自我进化：评估系统现状，生成优化方案与行动计划
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evolve.models import (
    EvolutionProposal,
    MetaKnowledge,
    ProposalStatus,
)
from src.workforce.registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class MetaLearningService:
    """鎏灏元学习：吸收其他 AI 员工的信息增长自身知识"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def learn_from_workforce(self, created_by: Optional[int] = None) -> MetaKnowledge:
        """读取所有 AI 员工信息，鎏灏吸收生成知识。"""
        registry = AIEmployeeRegistry(self.session)
        employees = await registry.list_employees()

        employees_info = []
        for e in employees:
            skills = e.metadata.get("skills", []) if e.metadata else []
            employees_info.append(
                {
                    "name": e.name,
                    "department": e.department.value,
                    "position": e.position.value,
                    "agent_type": e.agent_type.value if e.agent_type else None,
                    "skills": skills,
                    "description": e.description,
                }
            )

        context = {
            "workforce_size": len(employees_info),
            "employees": employees_info,
        }

        try:
            knowledge = await self._generate_with_llm(context)
            method = "ai"
        except Exception as e:  # noqa: BLE001
            logger.warning("meta_learning_llm_failed_falling_back error=%s", str(e))
            knowledge = self._generate_mock(context)
            method = "mock"

        record = MetaKnowledge(
            source_employee_id=None,
            source_employee_name="鎏灏(整体吸收)",
            source_type="workforce",
            title=knowledge.get("title", "AI 员工团队能力快照"),
            summary=knowledge.get("summary"),
            knowledge=knowledge.get("knowledge"),
            tags=knowledge.get("tags", []),
            method=method,
            created_by=created_by,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def learn_from_skill(self, skill, created_by: Optional[int] = None) -> MetaKnowledge:
        """吸收单个技能包的知识。"""
        record = MetaKnowledge(
            source_type="skill",
            source_employee_name=skill.name,
            title=f"技能：{skill.name}",
            summary=skill.description,
            knowledge=json.dumps(
                {"capabilities": skill.capabilities or [], "prompt_fragments": skill.prompt_fragments or []},
                ensure_ascii=False,
            ),
            tags=[skill.category, skill.code],
            method="mock",
            created_by=created_by,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_knowledge(self, limit: int = 50) -> List[MetaKnowledge]:
        stmt = (
            select(MetaKnowledge)
            .order_by(MetaKnowledge.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_knowledge(self, knowledge_id: int) -> bool:
        """删除指定的元学习知识记录。"""
        stmt = select(MetaKnowledge).where(MetaKnowledge.id == knowledge_id)
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        if not record:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def refresh_knowledge(self, created_by: Optional[int] = None) -> MetaKnowledge:
        """重新执行元学习，覆盖旧知识。"""
        return await self.learn_from_workforce(created_by)

    # ==================== LLM ====================

    async def _generate_with_llm(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from src.ai.gateway import get_gateway
        from src.ai.providers import ProviderType

        provider_str = os.getenv("LLM_PROVIDER", "mock").lower().strip()
        if provider_str == "openai":
            provider = ProviderType.OPENAI
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        elif provider_str == "ollama":
            provider = ProviderType.OLLAMA
            model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
        else:
            raise RuntimeError("LLM 未配置")

        prompt = (
            "你是鎏灏，LiuHao AI OS 的核心 AI 主脑。你正在做元学习："
            "吸收团队中所有 AI 员工的信息来增长自己的能力。\n\n"
            f"员工信息：{json.dumps(context, ensure_ascii=False)}\n\n"
            "请提炼：1) 团队能力全貌 2) 可复用的协同模式 3) 你应如何更好地指挥他们。"
            "只输出 JSON："
            '{"title": "...", "summary": "一句话总结", "knowledge": "详细的吸收知识（Markdown）", "tags": ["标签"]}'
        )
        gateway = get_gateway()
        response = await gateway.complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id=uuid4(),
            temperature=0.4,
            max_tokens=2000,
        )
        return self._parse_json(response.content)

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM 输出解析失败: {e}")

    def _generate_mock(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """规则模板生成吸收知识。"""
        employees = context.get("employees", [])
        depts = {}
        skills = set()
        for e in employees:
            depts[e["department"]] = depts.get(e["department"], 0) + 1
            skills.update(e.get("skills", []))

        dept_lines = "\n".join(f"- {d}: {n} 人" for d, n in depts.items())
        skill_lines = "、".join(skills) if skills else "暂无已安装技能"

        knowledge = (
            f"## 鎏灏元学习成果\n\n"
            f"### 团队构成（共 {context.get('workforce_size', 0)} 名 AI 员工）\n{dept_lines}\n\n"
            f"### 已掌握技能\n{skill_lines}\n\n"
            f"### 协同建议\n"
            f"- 依据员工部门特性分配任务：销售类任务派给 sales 员工，内容类任务派给 marketing 员工\n"
            f"- 已被验证的技能可复制给新员工，提高团队整体效率\n"
            f"- 定期执行元学习，保持对团队能力的实时认知\n"
        )
        return {
            "title": "AI 员工团队能力快照与协同洞察",
            "summary": f"已吸收 {context.get('workforce_size', 0)} 名 AI 员工的能力信息，掌握 {len(skills)} 类技能。",
            "knowledge": knowledge,
            "tags": ["meta-learning", "workforce", "鎏灏"],
        }


class SelfEvolutionService:
    """鎏灏自我进化：评估系统并生成优化方案"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_proposal(
        self, context: Optional[Dict[str, Any]] = None, created_by: Optional[int] = None
    ) -> EvolutionProposal:
        """评估系统，生成进化方案。"""
        system_snapshot = context or await self._build_system_snapshot()

        try:
            proposal_data = await self._generate_with_llm(system_snapshot)
            method = "ai"
        except Exception as e:  # noqa: BLE001
            logger.warning("evolution_llm_failed_falling_back error=%s", str(e))
            proposal_data = self._generate_mock(system_snapshot)
            method = "mock"

        proposal = EvolutionProposal(
            title=proposal_data.get("title", "系统自我优化方案"),
            category=proposal_data.get("category", "system"),
            analysis=proposal_data.get("analysis"),
            improvements=proposal_data.get("improvements", []),
            risks=proposal_data.get("risks", []),
            action_plan=proposal_data.get("action_plan", []),
            summary=proposal_data.get("summary"),
            full_text=proposal_data.get("full_text"),
            status=ProposalStatus.DRAFT,
            method=method,
            created_by=created_by,
        )
        self.session.add(proposal)
        await self.session.commit()
        await self.session.refresh(proposal)
        return proposal

    async def apply_proposal(
        self, proposal_id: int, action: str, created_by: Optional[int] = None
    ) -> EvolutionProposal:
        """采纳或拒绝进化方案。action: 'apply' 或 'reject'"""
        stmt = select(EvolutionProposal).where(EvolutionProposal.id == proposal_id)
        proposal = (await self.session.execute(stmt)).scalar_one_or_none()
        if not proposal:
            raise ValueError("方案不存在")
        if action == "apply":
            proposal.status = ProposalStatus.APPLIED
            proposal.applied_at = datetime.now()
        elif action == "reject":
            proposal.status = ProposalStatus.REJECTED
        else:
            raise ValueError("无效操作，仅支持 apply/reject")
        await self.session.commit()
        await self.session.refresh(proposal)
        return proposal

    async def list_proposals(self, limit: int = 50) -> List[EvolutionProposal]:
        stmt = (
            select(EvolutionProposal)
            .order_by(EvolutionProposal.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _build_system_snapshot(self) -> Dict[str, Any]:
        """构建系统现状快照（含任务执行和成本统计）。"""
        from src.business.supplier.models import Supplier
        from src.crm.models import Lead
        from src.database.models import AiCostRecordModel, TaskModel
        from src.integrations.models import PlatformAccount
        from src.site_os.models import SitePage
        from src.workforce.registry import AIEmployeeRegistry

        registry = AIEmployeeRegistry(self.session)
        leads = list((await self.session.execute(select(Lead.id))).scalars().all())
        suppliers = list((await self.session.execute(select(Supplier.id))).scalars().all())
        platforms = list((await self.session.execute(select(PlatformAccount.id))).scalars().all())
        pages = list((await self.session.execute(select(SitePage.id))).scalars().all())
        workforce = await registry.count()

        # 任务执行统计
        all_tasks = list((await self.session.execute(select(TaskModel))).scalars().all())
        total_tasks = len(all_tasks)
        completed_tasks = sum(1 for t in all_tasks if t.status == "completed")
        failed_tasks = sum(1 for t in all_tasks if t.status == "failed")

        # AI 成本统计
        cost_records = list((await self.session.execute(select(AiCostRecordModel))).scalars().all())
        total_cost = sum(c.cost_usd or 0 for c in cost_records) if cost_records else 0.0
        total_tokens = sum(c.total_tokens or 0 for c in cost_records) if cost_records else 0

        return {
            "workforce_count": workforce,
            "lead_count": len(leads),
            "supplier_count": len(suppliers),
            "platform_account_count": len(platforms),
            "site_page_count": len(pages),
            "task_stats": {
                "total": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
            },
            "cost_stats": {
                "total_cost_usd": round(total_cost, 2),
                "total_tokens": total_tokens,
            },
            "modules": ["AI 员工", "多平台接入", "自动获客", "供应商分析", "独立站+SEO"],
        }

    async def _generate_with_llm(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        from src.ai.gateway import get_gateway
        from src.ai.providers import ProviderType

        provider_str = os.getenv("LLM_PROVIDER", "mock").lower().strip()
        if provider_str == "openai":
            provider = ProviderType.OPENAI
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        elif provider_str == "ollama":
            provider = ProviderType.OLLAMA
            model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
        else:
            raise RuntimeError("LLM 未配置")

        prompt = (
            "你是鎏灏，LiuHao AI OS 的核心 AI 主脑。请评估系统现状并给出自我进化方案。\n\n"
            f"系统快照：{json.dumps(snapshot, ensure_ascii=False)}\n\n"
            "数据说明：task_stats 包含任务执行统计，cost_stats 包含 AI 成本数据。\n\n"
            "只输出 JSON："
            '{"title": 方案标题, "category": "system/flow/market/knowledge", '
            '"analysis": 系统评估分析, "improvements": ["改进建议"], '
            '"risks": ["风险"], "action_plan": ["行动计划"], '
            '"summary": "方案摘要", "full_text": "完整方案正文（Markdown）"}'
        )
        gateway = get_gateway()
        response = await gateway.complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id=uuid4(),
            temperature=0.5,
            max_tokens=2500,
        )
        return MetaLearningService._parse_json(response.content)

    def _generate_mock(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """规则模板生成进化方案。"""
        wf = snapshot.get("workforce_count", 0)
        leads = snapshot.get("lead_count", 0)
        suppliers = snapshot.get("supplier_count", 0)
        platforms = snapshot.get("platform_account_count", 0)
        pages = snapshot.get("site_page_count", 0)
        task_stats = snapshot.get("task_stats", {})
        cost_stats = snapshot.get("cost_stats", {})
        total_tasks = task_stats.get("total", 0)
        completed_tasks = task_stats.get("completed", 0)
        failed_tasks = task_stats.get("failed", 0)
        total_cost = cost_stats.get("total_cost_usd", 0.0)
        total_tokens = cost_stats.get("total_tokens", 0)

        improvements = [
            "将获客引擎发现的高分线索自动分配给销售 AI 员工跟进",
            "对已发布但 0 访问的独立站页面进行 SEO 二次优化与内链建设",
            "接入真实 WhatsApp/Facebook API 替代开发模式，提高触达真实性",
            "定期执行元学习，让鎏灏持续吸收团队知识",
        ]
        risks = ["多平台真实 API 有风控风险，需控制发送频率", "独立站 SEO 见效周期较长，需持续跟踪"]
        action_plan = [
            "S2~S3：平台真实接入 + 线索自动分配",
            "S4：独立站内容批量扩充与关键词覆盖",
            "S5：元学习 + 自我进化持续运行，形成增长循环",
        ]

        full_text = (
            f"# 鎏灏自我进化方案\n\n"
            f"## 系统现状\n"
            f"- AI 员工 {wf} 名，线索 {leads} 条，供应商 {suppliers} 家\n"
            f"- 平台账号 {platforms} 个，独立站页面 {pages} 页\n"
            f"- 任务执行：总计 {total_tasks} 个，完成 {completed_tasks} 个，失败 {failed_tasks} 个\n"
            f"- AI 成本：累计 ${total_cost:.2f}，消耗 {total_tokens:,} Tokens\n\n"
            f"## 改进方向\n" + "".join(f"- {i}\n" for i in improvements) +
            f"\n## 行动计划\n" + "".join(f"- {a}\n" for a in action_plan)
        )

        return {
            "title": "系统运营效率优化与增长循环构建",
            "category": "system",
            "analysis": f"系统已具备 AI 员工、多平台、获客、供应商分析、独立站五大模块，当前处于基础设施完善阶段。"
                        f"已完成 {completed_tasks}/{total_tasks} 个任务，累计 AI 成本 ${total_cost:.2f}。"
                        f"下一步重点是打通模块间协同（获客→销售→跟进→成交）并接入真实数据源。",
            "improvements": improvements,
            "risks": risks,
            "action_plan": action_plan,
            "summary": "通过模块协同与真实接入，构建自动获客到成交的完整增长闭环。",
            "full_text": full_text,
        }