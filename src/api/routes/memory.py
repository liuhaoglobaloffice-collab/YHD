"""
P1-G6.2: 企业记忆统一 CRUD API（MemoryPage 后端）。

基于 P1-G6.1 的 EnterpriseMemory facade 统一双记忆系统：
- 业务键值记忆（MemoryService -> memories 表）
- AI 员工会话记忆（AgentMemoryStore -> agent_memories 表）

端点：
- GET    /memory/overview          双系统分级统计（knowledge read）
- GET    /memory/items             统一列表 + origin/kind/agent_id 过滤（knowledge read）
- POST   /memory/business          新增业务键值记忆（knowledge write）
- DELETE /memory/business/{id}     删除业务记忆（knowledge delete，归属+审计门控）
- DELETE /memory/agent/{id}        删除会话记忆（knowledge delete，归属校验在 facade）
- POST   /memory/agent/{id}/core   标记/取消核心保留（knowledge write）
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.core.errors import NotFoundError
from src.identity.models import User
from src.knowledge.enterprise_memory import EnterpriseMemory
from src.knowledge.memory import MemoryType

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


async def get_enterprise_memory(
    session: AsyncSession = Depends(get_db),
) -> EnterpriseMemory:
    """每请求构建 EnterpriseMemory facade（RBAC + 审计落库由 facade 内部处理）。"""
    return EnterpriseMemory(session)


class BusinessMemoryCreateRequest(BaseModel):
    """新增业务键值记忆请求（老板手动添加的规则/偏好/事实）。"""

    key: str = Field(..., min_length=1, max_length=200)
    value: str = Field(..., min_length=1, max_length=2000)
    memory_type: str = Field(default="long_term")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class AgentCoreRequest(BaseModel):
    """会话记忆核心标记请求。"""

    is_core: bool = True


@router.get("/overview")
async def memory_overview(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """双系统记忆分级统计（业务键值 + AI 员工会话）。"""
    try:
        return await facade.overview(current_user)
    except Exception as e:
        logger.error("memory_overview_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Memory overview failed: {e}")


@router.get("/items")
async def list_memory_items(
    origin: Optional[str] = None,
    kind: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 200,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """统一列表：合并双系统记忆，标记 origin，支持 origin/kind/agent_id 过滤。"""
    if origin is not None and origin not in ("knowledge", "agent"):
        raise HTTPException(
            status_code=422, detail="origin 必须是 knowledge 或 agent"
        )
    try:
        items: List[Dict[str, Any]] = await facade.list_all(
            current_user, origin=origin, kind=kind, agent_id=agent_id, limit=limit
        )
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error("memory_items_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Memory list failed: {e}")


@router.post("/business")
async def create_business_memory(
    request: BusinessMemoryCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """新增业务键值记忆（RBAC + 审计由 MemoryService 内部保证）。"""
    try:
        memory_type = MemoryType(request.memory_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="memory_type 必须是 short_term / working / long_term",
        )
    try:
        item = await facade.remember_business(
            current_user,
            key=request.key,
            value=request.value,
            memory_type=memory_type,
            confidence=request.confidence,
            metadata=request.metadata,
        )
        logger.info(
            "business_memory_created",
            memory_id=item["id"],
            memory_type=memory_type.value,
            user_id=current_user.id,
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "business_memory_create_failed", error=str(e), user_id=current_user.id
        )
        raise HTTPException(status_code=500, detail=f"Memory creation failed: {e}")


@router.delete("/business/{memory_id}")
async def delete_business_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "delete")),
):
    """删除业务键值记忆。

    门控：knowledge:delete 权限 + facade 内部 RBAC/归属校验 + 审计落库。
    注：不使用 require_approval_for —— 该依赖对 delete 一律 403 且不检查
    已批准的审批请求（既有系统性缺陷，另行报告），会导致删除永久不可用。
    """
    try:
        result = await facade.delete(current_user, "knowledge", memory_id)
        logger.info(
            "business_memory_deleted", memory_id=memory_id, user_id=current_user.id
        )
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "business_memory_delete_failed", error=str(e), user_id=current_user.id
        )
        raise HTTPException(status_code=500, detail=f"Memory deletion failed: {e}")


@router.delete("/agent/{memory_id}")
async def delete_agent_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "delete")),
):
    """删除 AI 员工会话记忆（归属校验 + 审计在 facade 内部）。"""
    try:
        result = await facade.delete(current_user, "agent", memory_id)
        logger.info(
            "agent_memory_deleted", memory_id=memory_id, user_id=current_user.id
        )
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "agent_memory_delete_failed", error=str(e), user_id=current_user.id
        )
        raise HTTPException(status_code=500, detail=f"Agent memory deletion failed: {e}")


@router.post("/agent/{memory_id}/core")
async def mark_agent_memory_core(
    memory_id: str,
    request: AgentCoreRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facade: EnterpriseMemory = Depends(get_enterprise_memory),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """标记/取消会话记忆为核心（永久保留）。"""
    try:
        item = await facade.mark_agent_core(current_user, memory_id, request.is_core)
        if item.get("ok") is False:
            raise HTTPException(status_code=404, detail=f"记忆不存在: {memory_id}")
        return item
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "agent_memory_core_failed", error=str(e), user_id=current_user.id
        )
        raise HTTPException(status_code=500, detail=f"Agent memory core failed: {e}")