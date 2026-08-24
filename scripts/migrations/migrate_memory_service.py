#!/usr/bin/env python3
"""
LiuHao AI OS Y1.0
Phase 4 Module 1 - MemoryService Migration Script

Migrate MemoryService from Dict storage to Database Repository.
"""

import re


def migrate_memory_service():
    """Migrate MemoryService to use DatabaseRepository"""
    
    file_path = "src/knowledge/memory.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Backup
    with open(file_path + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    
    # 1. Update __init__ signature and implementation
    old_init = r'''def __init__\(
        self,
        rbac_service: RBACService,
        audit_service: AuditService,
    \):
        self\.rbac = rbac_service
        self\.audit = audit_service
        
        # In-memory storage \(will be replaced with database/cache\)
        self\._memories: Dict\[str, Memory\] = \{\}
        self\._user_memories: Dict\[str, List\[str\]\] = \{\}  # user_id -> memory_ids
        self\._session_memories: Dict\[str, List\[str\]\] = \{\}  # session_id -> memory_ids
        self\._task_memories: Dict\[str, List\[str\]\] = \{\}  # task_id -> memory_ids'''
    
    new_init = '''def __init__(
        self,
        session,  # AsyncSession
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        # Phase 4: Database integration
        self.session = session
        from ..database.repositories.knowledge import MemoryRepository
        self.repository = MemoryRepository(session)
        
        self.rbac = rbac_service
        self.audit = audit_service'''
    
    content = re.sub(old_init, new_init, content, flags=re.DOTALL)
    
    # 2. Add model converter after __init__
    converter = '''
    
    def _model_to_memory(self, model) -> Memory:
        """Convert MemoryModel to Memory dataclass"""
        from uuid import UUID
        return Memory(
            id=str(model.id),
            user_id=str(model.user_id),
            type=MemoryType(model.type),
            key=model.key,
            value=model.value,
            session_id=str(model.session_id) if model.session_id else None,
            task_id=str(model.task_id) if model.task_id else None,
            source=model.source,
            importance=model.importance,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )'''
    
    # Insert after __init__ block
    init_end = content.find("self.audit = audit_service")
    if init_end != -1:
        insert_pos = content.find("\n", init_end) + 1
        content = content[:insert_pos] + converter + "\n" + content[insert_pos:]
    
    # 3. Replace Dict storage operations in store() method
    # Find store method and replace memory storage
    store_pattern = r'(async def store\([\s\S]*?# Store memory\n\s+)self\._memories\[mem_id\] = memory'
    store_replacement = r'\1# Store in database\n        from uuid import UUID\n        from ..database.models import MemoryModel\n        \n        model = MemoryModel(\n            id=UUID(mem_id),\n            user_id=UUID(user.id),\n            type=memory_type.value,\n            key=key,\n            value=value,\n            session_id=UUID(session_id) if session_id else None,\n            task_id=UUID(task_id) if task_id else None,\n            source=source,\n            importance=importance,\n        )\n        model = await self.repository.create(model)\n        await self.session.commit()\n        memory = self._model_to_memory(model)'
    
    content = re.sub(store_pattern, store_replacement, content)
    
    # 4. Replace retrieve() method - get from database
    retrieve_pattern = r'(async def retrieve\([\s\S]*?# Get memory\n\s+)memory = self\._memories\.get\(memory_id\)'
    retrieve_replacement = r'\1# Get from database\n        from uuid import UUID\n        model = await self.repository.get_by_id(UUID(memory_id))\n        if not model:\n            return None\n        memory = self._model_to_memory(model)'
    
    content = re.sub(retrieve_pattern, retrieve_replacement, content)
    
    # 5. Replace list_user_memories() - query database
    list_user_pattern = r'(async def list_user_memories\([\s\S]*?# Get user memories\n\s+)memory_ids = self\._user_memories\.get\(user\.id, \[\]\)\n\s+return \[self\._memories\[mid\] for mid in memory_ids if mid in self\._memories\]'
    list_user_replacement = r'\1# Query from database\n        from uuid import UUID\n        models = await self.repository.list_by_user(UUID(user.id), memory_type)\n        return [self._model_to_memory(m) for m in models]'
    
    content = re.sub(list_user_pattern, list_user_replacement, content, flags=re.DOTALL)
    
    # 6. Replace delete() method - delete from database
    delete_pattern = r'(async def delete\([\s\S]*?# Delete memory\n\s+)if memory_id in self\._memories:\n\s+del self\._memories\[memory_id\]'
    delete_replacement = r'\1# Delete from database\n        from uuid import UUID\n        await self.repository.delete(UUID(memory_id))\n        await self.session.commit()'
    
    content = re.sub(delete_pattern, delete_replacement, content)
    
    # 7. Update imports - remove Dict from typing
    old_import = "from typing import Any, Dict, List, Optional"
    new_import = "from typing import Any, List, Optional"
    content = content.replace(old_import, new_import)
    
    # Write updated file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] MemoryService migrated to database")
    print("  - Added AsyncSession + Repository")
    print("  - Removed Dict storage")
    print("  - Added model converter")
    print("  - Updated all CRUD operations")


if __name__ == "__main__":
    migrate_memory_service()
