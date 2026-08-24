#!/usr/bin/env python3
"""
Fix MemoryService methods with precise line-by-line replacement
"""

def fix_memory_service():
    file_path = "src/knowledge/memory.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Backup
    with open(file_path + ".fix.bak", "w", encoding="utf-8") as f:
        f.write(content)
    
    # Fix 1: Update retrieve() to use database
    old_retrieve = '''        # Clean expired memories first
        self._clean_expired()
        
        # Get user memories
        memory_ids = self._user_memories.get(user.id, [])
        
        # Find matching memory
        for memory_id in memory_ids:
            memory = self._memories.get(memory_id)
            if not memory or not memory.is_active:
                continue
            
            # Check memory type
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Check session
            if session_id and memory.session_id != session_id:
                continue
            
            # Check task
            if task_id and memory.task_id != task_id:
                continue
            
            # Check key
            if memory.key == key:
                return memory
        
        return None'''
    
    new_retrieve = '''        # Query database by user and key
        models = await self.repository.list_by_user(user.id, memory_type)
        
        # Filter by key
        for model in models:
            memory = self._model_to_memory(model)
            if memory.key == key:
                return memory
        
        return None'''
    
    content = content.replace(old_retrieve, new_retrieve)
    
    # Fix 2: Update list_memories() to use database
    old_list = '''        # Get user memories
        memory_ids = self._user_memories.get(user.id, [])
        memories = []
        
        for memory_id in memory_ids:
            memory = self._memories.get(memory_id)
            if not memory or not memory.is_active:
                continue
            
            # Check memory type
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Check session
            if session_id and memory.session_id != session_id:
                continue
            
            # Check task
            if task_id and memory.task_id != task_id:
                continue
            
            memories.append(memory)
        
        return memories'''
    
    new_list = '''        # Query database
        models = await self.repository.list_by_user(user.id, memory_type)
        memories = [self._model_to_memory(m) for m in models]
        
        return memories'''
    
    content = content.replace(old_list, new_list)
    
    # Fix 3: Update delete() to use database
    old_delete = '''        # Get memory
        memory_id = str(memory_id)
        memory = self._memories.get(memory_id)
        
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")
        
        # Check ownership
        if memory.user_id != user.id and not self.rbac.is_admin(user):
            raise PermissionDeniedError("User does not own this memory")
        
        # Delete memory
        if memory_id in self._memories:
            del self._memories[memory_id]
        
        # Remove from indexes
        if user.id in self._user_memories and memory_id in self._user_memories[user.id]:
            self._user_memories[user.id].remove(memory_id)
        
        if memory.session_id and memory.session_id in self._session_memories:
            if memory_id in self._session_memories[memory.session_id]:
                self._session_memories[memory.session_id].remove(memory_id)
        
        if memory.task_id and memory.task_id in self._task_memories:
            if memory_id in self._task_memories[memory.task_id]:
                self._task_memories[memory.task_id].remove(memory_id)'''
    
    new_delete = '''        # Delete memory
        from uuid import UUID
        await self.repository.delete(UUID(memory_id))
        await self.session.commit()'''
    
    content = content.replace(old_delete, new_delete)
    
    # Write fixed file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] MemoryService methods fixed")
    print("  - retrieve() now uses Repository")
    print("  - list_memories() now uses Repository")
    print("  - delete() now uses Repository")


if __name__ == "__main__":
    fix_memory_service()
