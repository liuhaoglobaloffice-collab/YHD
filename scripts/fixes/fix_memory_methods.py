#!/usr/bin/env python3
"""
Fix MemoryService methods to use database instead of in-memory storage
"""

import re

# Read the file
with open("src/knowledge/memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix list_memories method
list_memories_old = r'''        # Clean expired memories first
        await self._clean_expired\(\)
        
        # Get user memories
        memory_ids = self._user_memories\.get\(user\.id, \[\]\)
        
        memories = \[\]
        for memory_id in memory_ids:
            memory = self\._memories\.get\(memory_id\)
            if not memory or not memory\.is_active:
                continue
            
            # Apply filters
            if memory_type and memory\.memory_type != memory_type:
                continue
            
            if session_id and memory\.session_id != session_id:
                continue
            
            if task_id and memory\.task_id != task_id:
                continue
            
            memories\.append\(memory\)'''

list_memories_new = '''        # Clean expired memories first
        await self._clean_expired()
        
        # Query database
        from ..database.models import MemoryModel
        from sqlalchemy import select, and_
        
        # Build query conditions
        conditions = [MemoryModel.user_id == str(user.id)]
        
        if memory_type:
            conditions.append(MemoryModel.memory_type == memory_type.value)
        if session_id:
            conditions.append(MemoryModel.session_id == session_id)
        if task_id:
            conditions.append(MemoryModel.task_id == task_id)
        
        # Query
        stmt = select(MemoryModel).where(and_(*conditions))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        # Convert to Memory objects
        memories = [self._model_to_memory(model) for model in models]'''

content = re.sub(list_memories_old, list_memories_new, content, flags=re.DOTALL)

# Fix delete method
delete_old = r'''        # Find memory
        memory = self\._memories\.get\(memory_id\)
        if not memory:
            raise NotFoundError\(f"Memory not found: \{memory_id\}"\)
        
        # Verify ownership
        if memory\.user_id != user\.id:
            raise PermissionDeniedError\("Cannot delete another user's memory"\)
        
        # Delete memory
        memory\.is_active = False
        del self\._memories\[memory_id\]
        
        # Remove from user index
        if user\.id in self\._user_memories:
            if memory_id in self\._user_memories\[user\.id\]:
                self\._user_memories\[user\.id\]\.remove\(memory_id\)'''

delete_new = '''        # Query database for memory
        from ..database.models import MemoryModel
        from sqlalchemy import select
        
        stmt = select(MemoryModel).where(MemoryModel.id == memory_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundError(f"Memory not found: {memory_id}")
        
        # Verify ownership
        if str(model.user_id) != str(user.id):
            raise PermissionDeniedError("Cannot delete another user's memory")
        
        # Delete from database
        await self.repository.delete(memory_id)
        await self.session.commit()'''

content = re.sub(delete_old, delete_new, content, flags=re.DOTALL)

# Fix clear_session method
clear_session_old = r'''        for memory_id in memory_ids:
            memory = self\._memories\.get\(memory_id\)
            if not memory or not memory\.is_active:
                continue
            
            if memory\.session_id == session_id:
                memory\.is_active = False
                cleared \+= 1'''

clear_session_new = '''        # Query and delete memories for session
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
            await self.session.commit()'''

content = re.sub(clear_session_old, clear_session_new, content, flags=re.DOTALL)

# Fix clear_task method  
clear_task_old = r'''        for memory_id in memory_ids:
            memory = self\._memories\.get\(memory_id\)
            if not memory or not memory\.is_active:
                continue
            
            if memory\.task_id == task_id:
                memory\.is_active = False
                cleared \+= 1'''

clear_task_new = '''        # Query and delete memories for task
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
            await self.session.commit()'''

content = re.sub(clear_task_old, clear_task_new, content, flags=re.DOTALL)

# Write back
with open("src/knowledge/memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed list_memories, delete, clear_session, clear_task methods")
