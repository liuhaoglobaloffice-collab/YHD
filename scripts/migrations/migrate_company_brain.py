#!/usr/bin/env python3
"""
LiuHao AI OS Y1.0
Phase 4 Module 1 - CompanyBrain Migration Script

Migrate CompanyBrain from Dict storage to Database Repository.
"""

import re


def migrate_company_brain():
    """Migrate CompanyBrain to use DatabaseRepository"""
    
    file_path = "src/knowledge/company_brain.py"
    
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
        
        # In-memory storage \(will be replaced with database\)
        self\._entities: Dict\[str, Entity\] = \{\}
        self\._facts: Dict\[str, Fact\] = \{\}'''
    
    new_init = '''def __init__(
        self,
        session,  # AsyncSession
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        # Phase 4: Database integration
        self.session = session
        from ..database.repositories.knowledge import CompanyBrainEntityRepository
        self.repository = CompanyBrainEntityRepository(session)
        
        self.rbac = rbac_service
        self.audit = audit_service'''
    
    content = re.sub(old_init, new_init, content, flags=re.DOTALL)
    
    # 2. Add model converter after __init__
    converter = '''
    
    def _model_to_entity(self, model) -> Entity:
        """Convert CompanyBrainEntityModel to Entity dataclass"""
        return Entity(
            id=str(model.id),
            entity_type=EntityType(model.entity_type),
            name=model.name,
            attributes=model.attributes or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=str(model.created_by) if model.created_by else None,
        )'''
    
    # Insert after __init__ block
    init_end = content.find("self.audit = audit_service")
    if init_end != -1:
        # Find the end of __init__ method
        next_line = content.find("\n\n", init_end)
        if next_line != -1:
            content = content[:next_line] + converter + content[next_line:]
    
    # 3. Replace create_entity() - store in database
    create_pattern = r'(async def create_entity\([\s\S]*?# Store entity\n\s+)self\._entities\[entity_id\] = entity'
    create_replacement = r'\1# Store in database\n        from uuid import UUID\n        from ..database.models import CompanyBrainEntityModel\n        \n        model = CompanyBrainEntityModel(\n            id=UUID(entity_id),\n            entity_type=entity_type.value,\n            name=name,\n            attributes=attributes,\n            created_by=UUID(user.id),\n        )\n        model = await self.repository.create(model)\n        await self.session.commit()\n        entity = self._model_to_entity(model)'
    
    content = re.sub(create_pattern, create_replacement, content)
    
    # 4. Replace get_entity() - retrieve from database
    get_pattern = r'(async def get_entity\([\s\S]*?# Get entity\n\s+)return self\._entities\.get\(entity_id\)'
    get_replacement = r'\1# Get from database\n        from uuid import UUID\n        model = await self.repository.get_by_id(UUID(entity_id))\n        if not model:\n            return None\n        return self._model_to_entity(model)'
    
    content = re.sub(get_pattern, get_replacement, content)
    
    # 5. Replace list_entities() - query database
    list_pattern = r'(async def list_entities\([\s\S]*?# List entities\n\s+)entities = list\(self\._entities\.values\(\)\)\n\s+if entity_type:\n\s+entities = \[e for e in entities if e\.entity_type == entity_type\]\n\s+return entities'
    list_replacement = r'\1# Query from database\n        models = await self.repository.list_by_type(entity_type.value if entity_type else None)\n        return [self._model_to_entity(m) for m in models]'
    
    content = re.sub(list_pattern, list_replacement, content, flags=re.DOTALL)
    
    # 6. Replace update_entity() - update in database
    update_pattern = r'(async def update_entity\([\s\S]*?# Update entity\n\s+)if entity_id not in self\._entities:\n\s+raise ValueError\(f"Entity \{entity_id\} not found"\)\n\s+\n\s+entity = self\._entities\[entity_id\]'
    update_replacement = r'\1# Update in database\n        from uuid import UUID\n        model = await self.repository.get_by_id(UUID(entity_id))\n        if not model:\n            raise ValueError(f"Entity {entity_id} not found")\n        \n        entity = self._model_to_entity(model)'
    
    content = re.sub(update_pattern, update_replacement, content, flags=re.DOTALL)
    
    # 7. Add database update after entity modification in update_entity()
    update_save_pattern = r'(entity\.updated_at = datetime\.now\(UTC\)\n\s+)self\._entities\[entity_id\] = entity'
    update_save_replacement = r'\1# Save to database\n        model.name = entity.name\n        model.attributes = entity.attributes\n        model.updated_at = entity.updated_at\n        await self.repository.update(model)\n        await self.session.commit()'
    
    content = re.sub(update_save_pattern, update_save_replacement, content)
    
    # 8. Replace delete_entity() - delete from database
    delete_pattern = r'(async def delete_entity\([\s\S]*?# Delete entity\n\s+)if entity_id in self\._entities:\n\s+del self\._entities\[entity_id\]'
    delete_replacement = r'\1# Delete from database\n        from uuid import UUID\n        await self.repository.delete(UUID(entity_id))\n        await self.session.commit()'
    
    content = re.sub(delete_pattern, delete_replacement, content)
    
    # Write updated file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] CompanyBrain migrated to database")
    print("  - Added AsyncSession + Repository")
    print("  - Removed Dict storage")
    print("  - Added model converter")
    print("  - Updated all entity operations")


if __name__ == "__main__":
    migrate_company_brain()
