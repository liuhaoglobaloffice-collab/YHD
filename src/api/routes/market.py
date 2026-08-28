"""
S5 AI 员工市场 + 元学习 + 自我进化 API.

提供员工市场（模板/技能包）、鎏灏元学习、自我进化方案端点。
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.evolve.growth import MetaLearningService, SelfEvolutionService
from src.evolve.market import MarketService
from src.evolve.models import EmployeeTemplate, EvolutionProposal, MetaKnowledge, SkillPack
from src.identity.audit import AuditService
from src.identity.models import User
from src.workforce.registry import AIEmployeeRegistry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


# ==================== Schemas ====================


class TemplateInstallRequest(BaseModel):
    template_id: int = Field(..., ge=1)


class SkillInstallRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    skill_id: int = Field(..., ge=1)


class EvolutionContextRequest(BaseModel):
    context: Optional[Dict[str, Any]] = None


# ==================== 序列化 ====================


def _template_out(t: EmployeeTemplate) -> Dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "department": t.department,
        "position": t.position,
        "description": t.description,
        "agent_type": t.agent_type,
        "category": t.category.value,
        "author": t.author,
        "version": t.version,
        "price": t.price,
        "rating": t.rating,
        "installs": t.installs,
        "skill_ids": t.skill_ids or [],
    }


def _skill_out(s: SkillPack) -> Dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "code": s.code,
        "description": s.description,
        "category": s.category,
        "capabilities": s.capabilities or [],
        "is_system": s.is_system,
        "version": s.version,
    }


def _knowledge_out(k: MetaKnowledge) -> Dict[str, Any]:
    return {
        "id": k.id,
        "source_employee_id": k.source_employee_id,
        "source_employee_name": k.source_employee_name,
        "source_type": k.source_type,
        "title": k.title,
        "summary": k.summary,
        "knowledge": k.knowledge,
        "tags": k.tags or [],
        "method": k.method,
        "created_at": k.created_at.isoformat(),
    }


def _proposal_out(p: EvolutionProposal) -> Dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "category": p.category,
        "analysis": p.analysis,
        "improvements": p.improvements or [],
        "risks": p.risks or [],
        "action_plan": p.action_plan or [],
        "summary": p.summary,
        "full_text": p.full_text,
        "status": p.status.value,
        "method": p.method,
        "created_at": p.created_at.isoformat(),
    }


def _employee_out(e) -> Dict[str, Any]:
    data = e.to_dict()
    skills = (e.metadata or {}).get("skills", []) if hasattr(e, "metadata") else []
    data["skills"] = skills
    data["market_category"] = (e.metadata or {}).get("market_category") if hasattr(e, "metadata") else None
    return data


# ==================== 员工市场 ====================


@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """AI 员工市场模板列表（内部/外部）。"""
    service = MarketService(session)
    result = await service.list_templates(category, keyword)
    return {
        "items": [_template_out(t) for t in result["items"]],
        "total": result["total"],
    }


@router.post("/templates/install", status_code=201)
async def install_template(
    request: TemplateInstallRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("employee", "create")),
):
    """从市场模板创建 AI 员工（内部/外部）。"""
    service = MarketService(session)
    template = await service.get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    employee = await service.install_template(template, current_user.id, current_user.tenant_id)

    await AuditService.log_success(
        session=session,
        action="install_employee_template",
        resource_type="employee",
        user_id=current_user.id,
        resource_id=str(employee.id),
        details={"template": template.name, "category": template.category.value},
    )
    return _employee_out(employee)


@router.get("/skills")
async def list_skill_packs(
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """技能包列表。"""
    service = MarketService(session)
    skills = await service.list_skill_packs(category, keyword)
    return {"items": [_skill_out(s) for s in skills], "total": len(skills)}


@router.post("/skills/install")
async def install_skill(
    request: SkillInstallRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("employee", "update")),
):
    """给 AI 员工安装技能包。"""
    service = MarketService(session)
    skill = (
        await session.execute(select(SkillPack).where(SkillPack.id == request.skill_id))
    ).scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能包不存在")
    try:
        employee = await service.install_skill(request.employee_id, skill, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _employee_out(employee)


# ==================== 鎏灏元学习 ====================


@router.post("/meta-learning/run")
async def run_meta_learning(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """鎏灏执行元学习：吸收团队 AI 员工知识。"""
    service = MetaLearningService(session)
    knowledge = await service.learn_from_workforce(current_user.id)
    await AuditService.log_success(
        session=session,
        action="meta_learning",
        resource_type="knowledge",
        user_id=current_user.id,
        resource_id=str(knowledge.id),
        details={"method": knowledge.method},
    )
    return _knowledge_out(knowledge)


@router.get("/meta-learning")
async def list_meta_knowledge(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """查看鎏灏已吸收的知识。"""
    service = MetaLearningService(session)
    items = await service.list_knowledge()
    return {"items": [_knowledge_out(k) for k in items], "total": len(items)}


# ==================== 自我进化 ====================


@router.post("/evolution/generate")
async def generate_evolution(
    request: EvolutionContextRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """鎏灏自我进化：评估系统生成优化方案。"""
    service = SelfEvolutionService(session)
    proposal = await service.generate_proposal(request.context, current_user.id)
    await AuditService.log_success(
        session=session,
        action="self_evolution",
        resource_type="proposal",
        user_id=current_user.id,
        resource_id=str(proposal.id),
        details={"method": proposal.method, "category": proposal.category},
    )
    return _proposal_out(proposal)


@router.get("/evolution")
async def list_proposals(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """查看鎏灏的进化方案。"""
    service = SelfEvolutionService(session)
    items = await service.list_proposals()
    return {"items": [_proposal_out(p) for p in items], "total": len(items)}


# ==================== 团队查看 ====================


@router.get("/employees")
async def list_ai_employees(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("employee", "read")),
):
    """查看当前 AI 员工团队（含技能/来源）。"""
    registry = AIEmployeeRegistry(session)
    employees = await registry.list_employees()
    return {"items": [_employee_out(e) for e in employees], "total": len(employees)}


# ==================== 进化方案操作 ====================


class ProposalActionRequest(BaseModel):
    action: str = Field(..., pattern="^(apply|reject)$")


@router.patch("/evolution/{proposal_id}")
async def update_proposal(
    proposal_id: int,
    request: ProposalActionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """采纳或拒绝进化方案。"""
    service = SelfEvolutionService(session)
    try:
        proposal = await service.apply_proposal(proposal_id, request.action, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await AuditService.log_success(
        session=session,
        action="proposal_" + request.action,
        resource_type="proposal",
        user_id=current_user.id,
        resource_id=str(proposal.id),
        details={"title": proposal.title, "status": proposal.status.value},
    )
    return _proposal_out(proposal)


# ==================== 元学习知识管理 ====================


@router.delete("/meta-learning/{knowledge_id}", status_code=204)
async def delete_meta_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """删除指定的元学习知识记录。"""
    service = MetaLearningService(session)
    deleted = await service.delete_knowledge(knowledge_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="知识记录不存在")


@router.post("/meta-learning/refresh")
async def refresh_meta_learning(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """重新执行元学习，刷新知识。"""
    service = MetaLearningService(session)
    knowledge = await service.refresh_knowledge(current_user.id)
    await AuditService.log_success(
        session=session,
        action="meta_learning_refresh",
        resource_type="knowledge",
        user_id=current_user.id,
        resource_id=str(knowledge.id),
        details={"method": knowledge.method},
    )
    return _knowledge_out(knowledge)