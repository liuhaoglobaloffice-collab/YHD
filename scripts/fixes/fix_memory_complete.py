#!/usr/bin/env python3
"""
Complete fix for MemoryService database migration
"""

import re

with open("src/knowledge/memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove broken FIXME comments
content = content.replace("# FIXME: Old code", "")
content = content.replace("# self._memories  ", "self._memories")
content = content.replace("# self._user_memories  ", "self._user_memories")

# Fix delete method completely
delete_pattern = r'(async def delete\([^)]+\) -> None:\s+"""[^"]*""")\s+# Permission check.*?# Audit log\s+await self\.audit\.log\([^)]+\)'

delete_replacement = r'''\1
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="delete_memory",
                resource_type="memory",
                resource_id=memory_id,
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")
        
        # Query database for memory
        from ..database.models import MemoryModel
        from sqlalchemy import select
        
        stmt = select(MemoryModel).where(MemoryModel.id == memory_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundError(f"Memory not found: {memory_id}")
        
        # Verify ownership
        if str(model.user_id) != str(user.id) and not self.rbac.is_admin(user):
            raise PermissionDeniedError("Cannot delete another user's memory")
        
        # Delete from database
        await self.repository.delete(memory_id)
        await self.session.commit()
        
        # Audit log
        await self.audit.log(
            action=AuditAction.DELETE,
            user_id=user.id,
            resource_type="memory",
            resource_id=memory_id,
        )'''

content = re.sub(delete_pattern, delete_replacement, content, flags=re.DOTALL)

# Fix clear_session method
clear_session_pattern = r'(async def clear_session\([^)]+\) -> int:\s+"""[^"]*""")\s+# Permission check.*?return cleaned'

clear_session_replacement = r'''\1
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="clear_session",
                resource_type="memory",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")
        
        await self._clean_expired()
        
        cleared = 0
        
        # Query and delete memories for session
        from ..database.models import MemoryModel
        from sqlalchemy import select
        
        stmt = select(MemoryModel).where(
            MemoryModel.user_id == str(user.id),
            MemoryModel.session_id == session_id
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        for model in models:
            await self.repository.delete(model.id)
            cleared += 1
        
        if cleared > 0:
            await self.session.commit()
        
        return cleared'''

content = re.sub(clear_session_pattern, clear_session_replacement, content, flags=re.DOTALL)

# Fix clear_task method
clear_task_pattern = r'(async def clear_task\([^)]+\) -> int:\s+"""[^"]*""")\s+# Permission check.*?return cleaned'

clear_task_replacement = r'''\1
        # Permission check
        if not self.rbac.has_permission(user, Permission.KNOWLEDGE_WRITE):
            await self.audit.log_permission_denied(
                user_id=user.id,
                action="clear_task",
                resource_type="memory",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_WRITE permission")
        
        await self._clean_expired()
        
        cleared = 0
        
        # Query and delete memories for task
        from ..database.models import MemoryModel
        from sqlalchemy import select
        
        stmt = select(MemoryModel).where(
            MemoryModel.user_id == str(user.id),
            MemoryModel.task_id == task_id
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        for model in models:
            await self.repository.delete(model.id)
            cleared += 1
        
        if cleared > 0:
            await self.session.commit()
        
        return cleared'''

content = re.sub(clear_task_pattern, clear_task_replacement, content, flags=re.DOTALL)

with open("src/knowledge/memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed delete, clear_session, clear_task methods")
