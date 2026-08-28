"""
AI 记忆层（V3）：Agent 会话记忆存储服务.

按 用户 × AI员工 自动保存对话/任务历史，并在下次执行时回忆注入，
让鎏灏跨会话记住前文上下文（Memory Recall）。

四级记忆分级策略：
- 短期（short-term）: 当前会话，7天内，全保留，之后自动清理
- 中期（medium-term）: 1个月内，保留重要对话（importance > 0.5）
- 长期（long-term）: 3个月以上，永久保留核心结论
- 核心（core）: 永远保留，关键业务决策/数据永不清理

- remember(): 写入单条记忆（user / assistant）
- remember_with_importance(): 写入带重要性评分的记忆
- recall():   取最近 N 条记忆（按时间正序）
- recall_important(): 优先召回重要记忆
- forget():   清空某 用户×员工 的记忆
- cleanup_expired(): 清理过期记忆（保留核心）
- export_memory(): 导出记忆到JSON
- import_memory(): 从JSON导入记忆
- get_memory_timeline(): 获取记忆时间轴
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentMemoryModel

# 注入上下文时最多回忆的轮次（条数）
DEFAULT_RECALL_LIMIT = 8

# 记忆分级过期时间（天）
EXPIRY_DAYS = {
    "short_term": 7,      # 7天后过期
    "medium_term": 30,    # 30天后过期
    "long_term": 180,     # 180天后过期（约6个月）
    "core": None,        # 永不过期
}


class MemoryLevel:
    """记忆分级常量"""
    SHORT = "short_term"
    MEDIUM = "medium_term"
    LONG = "long_term"
    CORE = "core"


class AgentMemoryStore:
    """Agent 会话记忆存储服务（四级分级存储版）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _calculate_expires(self, memory_level: str, importance: float) -> Optional[datetime]:
        """根据分级和重要性计算过期时间。"""
        days = EXPIRY_DAYS.get(memory_level)
        if days is None:
            return None
        # 重要性越高，保留越久 (+50% 时间)
        if importance > 0.8:
            days = int(days * 1.5)
        elif importance < 0.3:
            days = int(days * 0.5)
        return datetime.now(UTC) + timedelta(days=days)

    def _auto_level(self, content: str, role: str) -> Tuple[str, float]:
        """根据内容自动判断分级和重要性。

        简单启发式规则：
        - 包含结论/决策/总结 → 长期重要
        - 普通对话 → 短期
        - 用户提问 → 短期
        - AI回答长度长 → 更重要
        """
        content_lower = content.lower()
        importance = 0.5

        # 关键词判断重要性
        core_keywords = ["结论", "决策", "决定", "总结", "最终", "永久", "核心", "策略", "plan",
                         "decision", "conclusion", "final", "core", "strategy", "agreed"]
        for kw in core_keywords:
            if kw in content_lower:
                importance += 0.2

        # 长内容更可能重要
        if len(content) > 500:
            importance += 0.1
        elif len(content) < 50:
            importance -= 0.1

        importance = max(0.0, min(1.0, importance))

        # 根据重要性自动分级
        if importance >= 0.8:
            return MemoryLevel.CORE, importance
        elif importance >= 0.6:
            return MemoryLevel.LONG, importance
        elif importance >= 0.4:
            return MemoryLevel.MEDIUM, importance
        else:
            return MemoryLevel.SHORT, importance

    async def remember(
        self,
        user_id: int,
        agent_id: str,
        role: str,
        content: str,
        task_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        is_core: bool = False,
    ) -> AgentMemoryModel:
        """
        写入一条记忆。

        如果不指定 importance，会根据内容自动判断分级和重要性。
        """
        if not content.strip():
            raise ValueError("记忆内容不能为空")

        # 自动判断重要性和分级
        if importance is None:
            level, auto_imp = self._auto_level(content, role)
        else:
            # 根据重要性推断分级
            if importance >= 0.8:
                level = MemoryLevel.CORE
            elif importance >= 0.6:
                level = MemoryLevel.LONG
            elif importance >= 0.4:
                level = MemoryLevel.MEDIUM
            else:
                level = MemoryLevel.SHORT
            auto_imp = importance

        expires = self._calculate_expires(level, auto_imp)

        memory = AgentMemoryModel(
            user_id=user_id,
            agent_id=agent_id,
            role=role,
            content=content.strip(),
            task_id=task_id,
            memory_level=level,
            importance=auto_imp,
            is_core=is_core or level == MemoryLevel.CORE,
            expires_at=expires,
            meta=meta,
        )
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def remember_pair(
        self,
        user_id: int,
        agent_id: str,
        prompt: str,
        output: str,
        task_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        user_importance: Optional[float] = None,
        output_importance: Optional[float] = None,
    ) -> None:
        """成对写入：用户提问 + AI 回答。"""
        await self.remember(user_id, agent_id, "user", prompt, task_id, meta, user_importance)
        if output.strip():
            await self.remember(user_id, agent_id, "assistant", output, task_id, meta, output_importance)

    async def recall(
        self,
        user_id: int,
        agent_id: str,
        limit: int = DEFAULT_RECALL_LIMIT,
        include_expired: bool = False,
    ) -> List[AgentMemoryModel]:
        """
        取该 用户×员工 最近 limit 条记忆（时间正序，用于注入 Prompt）。
        默认只返回未过期的记忆。
        """
        conditions = [
            AgentMemoryModel.user_id == user_id,
            AgentMemoryModel.agent_id == agent_id,
        ]
        if not include_expired:
            now = datetime.now(UTC)
            conditions.append(
                (AgentMemoryModel.expires_at == None) | (AgentMemoryModel.expires_at > now)
            )

        stmt = (
            select(AgentMemoryModel)
            .where(and_(*conditions))
            .order_by(AgentMemoryModel.id.desc())
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        # 更新访问统计
        for row in rows:
            row.last_accessed_at = datetime.now(UTC)
            row.access_count += 1
        await self.session.commit()
        rows.reverse()
        return rows

    async def recall_important(
        self,
        user_id: int,
        agent_id: str,
        limit: int = DEFAULT_RECALL_LIMIT,
    ) -> List[AgentMemoryModel]:
        """优先召回重要记忆：先核心，再长期，再中期，最后短期。"""
        now = datetime.now(UTC)
        # 按重要性+时间排序，优先高重要性+近期
        stmt = (
            select(AgentMemoryModel)
            .where(
                AgentMemoryModel.user_id == user_id,
                AgentMemoryModel.agent_id == agent_id,
                (AgentMemoryModel.expires_at == None) | (AgentMemoryModel.expires_at > now),
            )
            .order_by(
                AgentMemoryModel.is_core.desc(),
                AgentMemoryModel.importance.desc(),
                AgentMemoryModel.id.desc(),
            )
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        # 更新访问统计
        for row in rows:
            row.last_accessed_at = datetime.now(UTC)
            row.access_count += 1
        await self.session.commit()
        # 保持时间顺序
        rows.sort(key=lambda r: r.id)
        return rows

    async def to_messages(
        self,
        user_id: int,
        agent_id: str,
        limit: int = DEFAULT_RECALL_LIMIT,
        add_system_hint: bool = True,
        prioritize_important: bool = False,
    ) -> List[Dict[str, str]]:
        """
        回忆记忆并转成给 LLM 的历史消息列表（可拼接前缀提示）。

        如果 prioritize_important=True，优先保留重要记忆。
        """
        if prioritize_important:
            history = await self.recall_important(user_id, agent_id, limit)
        else:
            history = await self.recall(user_id, agent_id, limit)

        messages: List[Dict[str, str]] = []
        if history and add_system_hint:
            if prioritize_important:
                hint = ("以下是该对话的重要历史记忆，请参考这些信息保持上下文连贯：\n"
                         "(核心记忆会永久保留，不重要的短期对话会被自动清理)")
            else:
                hint = "以下是与该用户的过往对话记录，请在需要时参考，保持上下文连贯："
            messages.append(
                {
                    "role": "system",
                    "content": hint,
                }
            )
        messages.extend(
            {"role": m.role if m.role in ("user", "assistant") else "user", "content": m.content}
            for m in history
        )
        return messages

    async def forget(self, user_id: int, agent_id: str) -> int:
        """清空该 用户×员工 的对话记忆，返回删除条数。"""
        result = await self.session.execute(
            delete(AgentMemoryModel).where(
                AgentMemoryModel.user_id == user_id,
                AgentMemoryModel.agent_id == agent_id,
            )
        )
        await self.session.commit()
        return result.rowcount or 0

    async def cleanup_expired(self, user_id: Optional[int] = None) -> Tuple[int, int]:
        """
        清理过期记忆。核心记忆永远保留。

        Returns:
            (deleted_count, total_before)
        """
        now = datetime.now(UTC)
        conditions = [
            AgentMemoryModel.is_core == False,  # noqa: E712
            AgentMemoryModel.expires_at < now,
        ]
        if user_id is not None:
            conditions.append(AgentMemoryModel.user_id == user_id)

        # 统计总数
        count_stmt = select(AgentMemoryModel.id).where(and_(*conditions))
        total_before = len(list((await self.session.execute(count_stmt)).scalars().all()))

        if total_before == 0:
            return (0, 0)

        # 删除过期
        result = await self.session.execute(delete(AgentMemoryModel).where(and_(*conditions)))
        await self.session.commit()
        deleted = result.rowcount or 0
        return (deleted, total_before)

    async def mark_core(
        self,
        memory_id: int,
        is_core: bool = True,
    ) -> Optional[AgentMemoryModel]:
        """将记忆标记为核心（永久保留）或取消标记。"""
        stmt = select(AgentMemoryModel).where(AgentMemoryModel.id == memory_id)
        memory = (await self.session.execute(stmt)).scalar_one_or_none()
        if not memory:
            return None
        memory.is_core = is_core
        if is_core:
            memory.expires_at = None
            memory.memory_level = MemoryLevel.CORE
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def export_memory(
        self,
        user_id: int,
        agent_id: str,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """导出用户-代理的所有记忆为JSON，可用于备份或迁移。"""
        conditions = [
            AgentMemoryModel.user_id == user_id,
            AgentMemoryModel.agent_id == agent_id,
        ]
        if not include_expired:
            now = datetime.now(UTC)
            conditions.append(
                (AgentMemoryModel.expires_at == None) | (AgentMemoryModel.expires_at > now)
            )

        stmt = (
            select(AgentMemoryModel)
            .where(and_(*conditions))
            .order_by(AgentMemoryModel.id.asc())
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return [m.to_dict() for m in rows]

    async def import_memory(
        self,
        exported_data: List[Dict[str, Any]],
    ) -> Tuple[int, int]:
        """从导出的JSON数据导入记忆。返回 (success, failed)。"""
        success, failed = 0, 0
        for item in exported_data:
            try:
                # 重新创建，保持原始id但数据库会自增，接受这个
                memory = AgentMemoryModel(
                    user_id=item["user_id"],
                    agent_id=item["agent_id"],
                    role=item["role"],
                    content=item["content"],
                    task_id=item.get("task_id"),
                    memory_level=item.get("memory_level", MemoryLevel.SHORT),
                    importance=item.get("importance", 0.5),
                    is_core=item.get("is_core", False),
                    meta=item.get("meta"),
                )
                # 重新计算过期时间从导入时间开始
                if not memory.is_core and memory.expires_at is None:
                    memory.expires_at = self._calculate_expires(memory.memory_level, memory.importance)
                self.session.add(memory)
                success += 1
            except Exception:
                failed += 1
        await self.session.commit()
        return (success, failed)

    async def get_memory_timeline(
        self,
        user_id: int,
        agent_id: str,
        days_back: int = 90,
    ) -> List[Dict[str, Any]]:
        """获取记忆时间轴，用于UI展示记忆演进。"""
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = (
            select(AgentMemoryModel)
            .where(
                AgentMemoryModel.user_id == user_id,
                AgentMemoryModel.agent_id == agent_id,
                AgentMemoryModel.created_at >= cutoff,
                (AgentMemoryModel.expires_at == None) | (AgentMemoryModel.expires_at > datetime.now(UTC)),
            )
            .order_by(AgentMemoryModel.created_at.asc())
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return [
            {
                "id": m.id,
                "role": m.role,
                "content_preview": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "memory_level": m.memory_level,
                "importance": m.importance,
                "is_core": m.is_core,
                "created_at": m.created_at.isoformat(),
                "access_count": m.access_count,
            }
            for m in rows
        ]

    async def count_memories(
        self,
        user_id: int,
        agent_id: str,
    ) -> Dict[str, int]:
        """统计各级别记忆数量。"""
        from sqlalchemy import func

        stmt = (
            select(
                AgentMemoryModel.memory_level,
                func.count(AgentMemoryModel.id)
            )
            .where(
                AgentMemoryModel.user_id == user_id,
                AgentMemoryModel.agent_id == agent_id,
            )
            .group_by(AgentMemoryModel.memory_level)
        )
        result = await self.session.execute(stmt)
        counts = {level: 0 for level in [MemoryLevel.SHORT, MemoryLevel.MEDIUM, MemoryLevel.LONG, MemoryLevel.CORE]}
        for level, cnt in result:
            counts[level] = cnt
        counts["total"] = sum(counts.values())
        counts["core_permanent"] = counts[MemoryLevel.CORE]
        return counts