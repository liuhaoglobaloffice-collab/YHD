"""
P1-G6.1: EnterpriseMemory 企业记忆统一门面（facade）。

现状：两套记忆系统并存，各自独立使用：
- src/knowledge/memory.MemoryService —— 业务键值记忆（short_term/working/long_term，
  RBAC 权限 + 审计日志，memories 表）
- src/ai/memory_store.AgentMemoryStore —— AI 员工会话记忆（short/medium/long/core
  四级分级，agent_memories 表）

本门面不改变两套系统的已验收行为，仅提供统一入口：
- remember_business / recall_business → 路由到 MemoryService
- remember_agent / recall_agent       → 路由到 AgentMemoryStore
- list_all   → 合并双系统记忆，统一结构并标记 origin
- delete     → 按 origin 路由删除（业务记忆走 RBAC+审计，会话记忆校验归属+审计）
- overview   → 双系统统计概览（供 MemoryPage / CRUD API 使用）
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from src.core.errors import NotFoundError, PermissionDeniedError
from src.database.models import AgentMemoryModel, MemoryModel
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.knowledge.memory import MemoryService, MemoryType

ORIGIN_KNOWLEDGE = "knowledge"  # 业务键值记忆（MemoryService）
ORIGIN_AGENT = "agent"          # AI 员工会话记忆（AgentMemoryStore）

KNOWLEDGE_KINDS = ("short_term", "working", "long_term")
AGENT_KINDS = ("short_term", "medium_term", "long_term", "core")


class _LegacyAuditAdapter:
    """旧式 audit 调用签名适配器。

    MemoryService / 本门面按 log(action=..., resource_type=...) 旧式关键字
    调用审计；真实 AuditService.log 是静态方法，要求
    (session, action, resource_type, status, ...)。此适配器补齐 session 与
    status，使审计在真实 API 链路下真正落库（G6.2 CRUD API 依赖）。
    """

    def __init__(self, session):
        self._session = session

    async def log(
        self,
        session,
        action,
        resource_type,
        status: str = "success",
        user_id=None,
        resource_id=None,
        details=None,
        error_message=None,
        ip_address=None,
        user_agent=None,
        **_ignored,
    ):
        # 签名对齐真实 AuditService.log(session, action, resource_type, status, ...)：
        # session 作为第一位置参数（调用方多按 self.audit.log(self.session, action=...) 调用）。
        return await AuditService.log(
            session=session or self._session,
            action=action,
            resource_type=resource_type,
            status=status,
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_permission_denied(
        self,
        user_id=None,
        action=None,
        resource_type=None,
        resource_id=None,
        reason=None,
        **_ignored,
    ):
        return await AuditService.log(
            session=self._session,
            action=action or "permission_check",
            resource_type=resource_type or "memory",
            status="denied",
            user_id=user_id,
            resource_id=resource_id,
            error_message=reason or "permission denied",
        )


class EnterpriseMemory:
    """统一企业记忆门面：一套 API 访问双记忆系统，输出统一结构并标记来源。"""

    def __init__(self, session, rbac_service=None, audit_service=None):
        from src.ai.memory_store import AgentMemoryStore  # 延迟导入避免包级循环依赖

        self.session = session
        self.rbac = rbac_service or RBACService(session)
        self.audit = audit_service or _LegacyAuditAdapter(session)
        self.business = MemoryService(
            session=session, rbac_service=self.rbac, audit_service=self.audit
        )
        self.agent = AgentMemoryStore(session)

    # ==================== 业务键值记忆（knowledge） ====================

    async def remember_business(
        self,
        user: User,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """写入业务键值记忆（老板手动添加的规则/偏好/事实）。"""
        mem = await self.business.store(
            user=user,
            memory_type=memory_type,
            key=key,
            value=value,
            session_id=session_id,
            task_id=task_id,
            source="enterprise_memory",
            confidence=confidence,
            metadata=metadata,
        )
        return self._business_item(mem)

    async def recall_business(
        self,
        user: User,
        key: str,
        memory_type: Optional[MemoryType] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """按键召回业务记忆。"""
        mem = await self.business.retrieve(user, key, memory_type, session_id, task_id)
        return self._business_item(mem) if mem else None

    # ==================== AI 员工会话记忆（agent） ====================

    async def remember_agent(
        self,
        user: User,
        agent_id: str,
        role: str,
        content: str,
        task_id: Optional[str] = None,
        importance: Optional[float] = None,
        is_core: bool = False,
    ) -> Dict[str, Any]:
        """写入 AI 员工会话记忆（user × agent）。"""
        mem = await self.agent.remember(
            user_id=user.id,
            agent_id=agent_id,
            role=role,
            content=content,
            task_id=task_id,
            importance=importance,
            is_core=is_core,
        )
        return self._agent_item(mem)

    async def recall_agent(
        self,
        user: User,
        agent_id: str,
        limit: int = 8,
        prioritize_important: bool = False,
    ) -> List[Dict[str, Any]]:
        """召回该 用户×员工 的会话记忆（时间正序）。"""
        if prioritize_important:
            rows = await self.agent.recall_important(user.id, agent_id, limit)
        else:
            rows = await self.agent.recall(user.id, agent_id, limit)
        return [self._agent_item(m) for m in rows]

    async def recall_agent_messages(
        self,
        user: User,
        agent_id: str,
        limit: int = 8,
        prioritize_important: bool = False,
    ) -> List[Dict[str, str]]:
        """召回并转成 LLM 历史消息（供执行链路注入上下文）。"""
        return await self.agent.to_messages(
            user.id, agent_id, limit=limit, prioritize_important=prioritize_important
        )

    # ==================== 统一列表 ====================

    async def list_all(
        self,
        user: User,
        origin: Optional[str] = None,
        kind: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """合并双系统记忆（统一结构 + origin 标记），按创建时间倒序。

        kind 为统一分类：short_term/working/long_term（knowledge）与
        short_term/medium_term/long_term/core（agent）中同名值跨系统生效。
        """
        if origin not in (None, ORIGIN_KNOWLEDGE, ORIGIN_AGENT):
            raise ValueError(f"未知记忆来源: {origin}")

        items: List[Dict[str, Any]] = []
        if origin in (None, ORIGIN_KNOWLEDGE):
            mtype = MemoryType(kind) if kind in KNOWLEDGE_KINDS else None
            for mem in await self.business.list_memories(user, memory_type=mtype):
                items.append(self._business_item(mem))
        if origin in (None, ORIGIN_AGENT):
            stmt = select(AgentMemoryModel).where(AgentMemoryModel.user_id == user.id)
            if kind in AGENT_KINDS:
                stmt = stmt.where(AgentMemoryModel.memory_level == kind)
            if agent_id:
                stmt = stmt.where(AgentMemoryModel.agent_id == agent_id)
            stmt = stmt.order_by(AgentMemoryModel.id.desc()).limit(limit)
            rows = list((await self.session.execute(stmt)).scalars().all())
            items.extend(self._agent_item(m) for m in rows)

        items.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return items[:limit]

    # ==================== 删除 ====================

    async def delete(self, user: User, origin: str, memory_id: str) -> Dict[str, Any]:
        """按 origin 路由删除。

        业务记忆走 MemoryService（RBAC + 审计）；
        会话记忆校验归属（或超管）后删除并记审计。
        """
        if origin == ORIGIN_KNOWLEDGE:
            await self.business.delete(user, memory_id)
            return {"ok": True, "origin": origin, "id": memory_id}

        if origin == ORIGIN_AGENT:
            numeric_id = self._parse_agent_id(memory_id)
            model = await self._get_agent_memory(numeric_id)
            if model.user_id != user.id and not getattr(user, "is_superuser", False):
                raise PermissionDeniedError("不能删除其他用户的会话记忆")
            await self.session.execute(
                sa_delete(AgentMemoryModel).where(AgentMemoryModel.id == numeric_id)
            )
            await self.session.commit()
            await self.audit.log(
                self.session,
                action=AuditAction.DELETE,
                status="success",
                user_id=user.id,
                resource_type="agent_memory",
                resource_id=str(numeric_id),
                details={"agent_id": model.agent_id},
            )
            return {"ok": True, "origin": origin, "id": memory_id}

        raise ValueError(f"未知记忆来源: {origin}")

    async def mark_agent_core(
        self, user: User, memory_id: str, is_core: bool = True
    ) -> Dict[str, Any]:
        """将会话记忆标记/取消标记为核心（永久保留），校验归属。"""
        numeric_id = self._parse_agent_id(memory_id)
        model = await self._get_agent_memory(numeric_id)
        if model.user_id != user.id and not getattr(user, "is_superuser", False):
            raise PermissionDeniedError("不能修改其他用户的会话记忆")
        updated = await self.agent.mark_core(numeric_id, is_core)
        await self.audit.log(
            self.session,
            action=AuditAction.UPDATE,
            status="success",
            user_id=user.id,
            resource_type="agent_memory",
            resource_id=str(numeric_id),
            details={"is_core": is_core},
        )
        return self._agent_item(updated) if updated else {"ok": False}

    # ==================== 统计 ====================

    async def overview(self, user: User) -> Dict[str, Any]:
        """双系统记忆统计概览。"""
        k_rows = (
            await self.session.execute(
                select(MemoryModel.memory_type, func.count(MemoryModel.id))
                .where(MemoryModel.user_id == str(user.id))
                .group_by(MemoryModel.memory_type)
            )
        ).all()
        knowledge: Dict[str, int] = {k: 0 for k in KNOWLEDGE_KINDS}
        for k, cnt in k_rows:
            knowledge[k] = cnt
        knowledge["total"] = sum(v for k, v in knowledge.items() if k != "total")

        a_rows = (
            await self.session.execute(
                select(AgentMemoryModel.memory_level, func.count(AgentMemoryModel.id))
                .where(AgentMemoryModel.user_id == user.id)
                .group_by(AgentMemoryModel.memory_level)
            )
        ).all()
        agent: Dict[str, int] = {k: 0 for k in AGENT_KINDS}
        for k, cnt in a_rows:
            agent[k] = cnt
        agent["total"] = sum(v for k, v in agent.items() if k != "total")
        agent["core_permanent"] = agent["core"]

        return {
            "knowledge": knowledge,
            "agent": agent,
            "total": knowledge["total"] + agent["total"],
        }

    # ==================== 内部工具 ====================

    @staticmethod
    def _parse_agent_id(memory_id: str) -> int:
        try:
            return int(memory_id)
        except (TypeError, ValueError) as e:
            raise NotFoundError(f"记忆不存在: {memory_id}") from e

    async def _get_agent_memory(self, numeric_id: int) -> AgentMemoryModel:
        stmt = select(AgentMemoryModel).where(AgentMemoryModel.id == numeric_id)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if not model:
            raise NotFoundError(f"记忆不存在: {numeric_id}")
        return model

    @staticmethod
    def _business_item(mem) -> Dict[str, Any]:
        d = mem.to_dict()
        value = d.get("value")
        return {
            "id": d["id"],
            "origin": ORIGIN_KNOWLEDGE,
            "kind": d.get("memory_type"),
            "key": d.get("key"),
            "content": "" if value is None else str(value),
            "importance": float(d.get("confidence", 1.0)),
            "is_core": d.get("memory_type") == MemoryType.LONG_TERM.value,
            "created_at": d.get("created_at"),
            "meta": {"source": d.get("source"), "metadata": d.get("metadata")},
        }

    @staticmethod
    def _agent_item(m) -> Dict[str, Any]:
        created = getattr(m, "created_at", None)
        return {
            "id": str(m.id),
            "origin": ORIGIN_AGENT,
            "kind": m.memory_level,
            "key": m.agent_id,
            "content": m.content,
            "importance": float(m.importance or 0.5),
            "is_core": bool(m.is_core),
            "created_at": created.isoformat() if created else None,
            "meta": {"role": m.role, "task_id": m.task_id},
        }
