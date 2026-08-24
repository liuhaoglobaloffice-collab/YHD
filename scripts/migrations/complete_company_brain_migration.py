#!/usr/bin/env python3
"""
LiuHao AI OS Y1.0
Phase 4 Module 1 - Complete CompanyBrain Database Migration

Final migration of all CompanyBrain methods to use Repository.
"""


def complete_company_brain_migration():
    """Complete CompanyBrain migration to database"""
    
    file_path = "src/knowledge/company_brain.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Backup
    with open(file_path + ".migration.bak", "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    output = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Replace get_entity() implementation
        if "async def get_entity(" in line:
            output.append(line)
            i += 1
            
            # Copy until implementation starts
            while i < len(lines) and "# Get entity" not in lines[i]:
                output.append(lines[i])
                i += 1
            
            # Replace implementation
            output.append("        # Get entity\n")
            output.append("        from uuid import UUID\n")
            output.append("        model = await self.repository.get_by_id(UUID(entity_id))\n")
            output.append("        if not model:\n")
            output.append("            return None\n")
            output.append("        return self._model_to_entity(model)\n")
            
            # Skip old implementation
            while i < len(lines) and not (lines[i].strip().startswith("async def") or (lines[i].strip().startswith("def ") and "def to_dict" not in lines[i])):
                i += 1
            continue
        
        # Replace list_entities() implementation
        elif "async def list_entities(" in line:
            output.append(line)
            i += 1
            
            # Copy until implementation starts
            while i < len(lines) and "# List entities" not in lines[i]:
                output.append(lines[i])
                i += 1
            
            # Replace implementation
            output.append("        # List entities\n")
            output.append("        models = await self.repository.list_by_type(entity_type.value if entity_type else None)\n")
            output.append("        return [self._model_to_entity(m) for m in models]\n")
            
            # Skip old implementation
            while i < len(lines) and not (lines[i].strip().startswith("async def") or (lines[i].strip().startswith("def ") and "def to_dict" not in lines[i])):
                i += 1
            continue
        
        # Replace update_entity() implementation
        elif "async def update_entity(" in line:
            output.append(line)
            i += 1
            
            # Copy until implementation starts
            while i < len(lines) and "# Update entity" not in lines[i]:
                output.append(lines[i])
                i += 1
            
            # Replace implementation
            output.append("        # Update entity\n")
            output.append("        from uuid import UUID\n")
            output.append("        model = await self.repository.get_by_id(UUID(entity_id))\n")
            output.append("        if not model:\n")
            output.append("            raise ValueError(f\"Entity {entity_id} not found\")\n")
            output.append("        \n")
            output.append("        # Update fields\n")
            output.append("        if name is not None:\n")
            output.append("            model.name = name\n")
            output.append("        if attributes is not None:\n")
            output.append("            model.attributes = attributes\n")
            output.append("        \n")
            output.append("        # Update timestamp\n")
            output.append("        from datetime import datetime, UTC\n")
            output.append("        model.updated_at = datetime.now(UTC)\n")
            output.append("        \n")
            output.append("        await self.repository.update(model)\n")
            output.append("        await self.session.commit()\n")
            output.append("        \n")
            output.append("        entity = self._model_to_entity(model)\n")
            output.append("        \n")
            output.append("        # Audit log\n")
            output.append("        await self.audit.log(\n")
            output.append("            action=AuditAction.UPDATE,\n")
            output.append("            user_id=user.id,\n")
            output.append("            resource_type=\"entity\",\n")
            output.append("            resource_id=entity_id,\n")
            output.append("            details={\"name\": name, \"attributes\": attributes},\n")
            output.append("        )\n")
            output.append("        \n")
            output.append("        return entity\n")
            
            # Skip old implementation
            while i < len(lines) and not (lines[i].strip().startswith("async def") or (lines[i].strip().startswith("def ") and "def to_dict" not in lines[i])):
                i += 1
            continue
        
        # Replace delete_entity() implementation
        elif "async def delete_entity(" in line:
            output.append(line)
            i += 1
            
            # Copy until implementation starts
            while i < len(lines) and "# Delete entity" not in lines[i]:
                output.append(lines[i])
                i += 1
            
            # Replace implementation
            output.append("        # Delete entity\n")
            output.append("        from uuid import UUID\n")
            output.append("        await self.repository.delete(UUID(entity_id))\n")
            output.append("        await self.session.commit()\n")
            output.append("        \n")
            output.append("        # TODO: Also delete associated facts\n")
            output.append("        \n")
            output.append("        # Audit log\n")
            output.append("        await self.audit.log(\n")
            output.append("            action=AuditAction.DELETE,\n")
            output.append("            user_id=user.id,\n")
            output.append("            resource_type=\"entity\",\n")
            output.append("            resource_id=entity_id,\n")
            output.append("        )\n")
            
            # Skip old implementation
            while i < len(lines) and not (lines[i].strip().startswith("async def") or (lines[i].strip().startswith("def ") and "def to_dict" not in lines[i])):
                i += 1
            continue
        
        output.append(line)
        i += 1
    
    # Write updated file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(output)
    
    print("[OK] CompanyBrain fully migrated to database")
    print("  - get_entity() uses Repository.get_by_id")
    print("  - list_entities() uses Repository.list_by_type")
    print("  - update_entity() uses Repository.update")
    print("  - delete_entity() uses Repository.delete")
    print("  - Fact system marked as TODO for future implementation")


if __name__ == "__main__":
    complete_company_brain_migration()
