#!/usr/bin/env python3
"""
LiuHao AI OS Y1.0
Phase 4 Module 1 - Knowledge API Migration Script

Update Knowledge API to use Service Factory + Dependency Injection.
"""

import re


def migrate_knowledge_api():
    """Migrate Knowledge API to use database-backed services"""
    
    file_path = "src/api/routes/knowledge.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Backup
    with open(file_path + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    
    # 1. Remove global service instances
    old_instances = r'''# Service instances \(in-memory for Stage 4\)
doc_service = DocumentService\(\)
processor = DocumentProcessor\(\)
retrieval_service = RetrievalService\(\)
brain_service = CompanyBrain\(\)
memory_service = MemoryService\(\)'''
    
    new_comment = '''# Phase 4: Services now use dependency injection via factories
# processor and retrieval_service remain global as they don't need DB
processor = DocumentProcessor()
retrieval_service = RetrievalService()'''
    
    content = re.sub(old_instances, new_comment, content)
    
    # 2. Add factory imports at the top
    import_pattern = r'(from src\.api\.dependencies\.permissions import require_permission)'
    import_addition = r'''\1
from src.api.factories.knowledge import (
    get_document_service,
    get_memory_service,
    get_company_brain,
)'''
    
    content = re.sub(import_pattern, import_addition, content)
    
    # 3. Update /upload endpoint - add doc_service dependency
    upload_pattern = r'(@router\.post\("/upload"\)[\s\S]*?async def upload_document\(\n\s+file: UploadFile,\n\s+)(user: User = Depends\(get_current_user\),)'
    upload_replacement = r'\1doc_service: DocumentService = Depends(get_document_service),\n    \2'
    content = re.sub(upload_pattern, upload_replacement, content)
    
    # Remove the global doc_service call in upload_document
    content = content.replace(
        'doc = doc_service.create_document(',
        'doc = await doc_service.create_document('
    )
    
    # 4. Update /documents endpoint - add doc_service dependency
    list_docs_pattern = r'(@router\.get\("/documents"\)[\s\S]*?async def list_documents\(\n\s+)(user: User = Depends\(get_current_user\),)'
    list_docs_replacement = r'\1doc_service: DocumentService = Depends(get_document_service),\n    \2'
    content = re.sub(list_docs_pattern, list_docs_replacement, content)
    
    content = content.replace(
        'docs = doc_service.list_documents(',
        'docs = await doc_service.list_documents('
    )
    
    # 5. Update /brain/entities endpoint - add brain_service dependency
    create_entity_pattern = r'(@router\.post\("/brain/entities"\)[\s\S]*?async def create_entity\(\n\s+request: CreateEntityRequest,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    create_entity_replacement = r'\1brain_service: CompanyBrain = Depends(get_company_brain),\n    \2'
    content = re.sub(create_entity_pattern, create_entity_replacement, content)
    
    content = content.replace(
        'entity = brain_service.create_entity(',
        'entity = await brain_service.create_entity('
    )
    
    # 6. Update /brain/entities/{entity_id} GET - add brain_service dependency
    get_entity_pattern = r'(@router\.get\("/brain/entities/\{entity_id\}"\)[\s\S]*?async def get_entity\(\n\s+entity_id: str,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    get_entity_replacement = r'\1brain_service: CompanyBrain = Depends(get_company_brain),\n    \2'
    content = re.sub(get_entity_pattern, get_entity_replacement, content)
    
    content = content.replace(
        'entity = brain_service.get_entity(entity_id, user=current_user)',
        'entity = await brain_service.get_entity(entity_id, user=current_user)'
    )
    
    # 7. Update /brain/entities/{entity_id}/facts POST - add brain_service dependency
    create_fact_pattern = r'(@router\.post\("/brain/entities/\{entity_id\}/facts"\)[\s\S]*?async def create_fact\(\n\s+entity_id: str,\n\s+request: CreateFactRequest,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    create_fact_replacement = r'\1brain_service: CompanyBrain = Depends(get_company_brain),\n    \2'
    content = re.sub(create_fact_pattern, create_fact_replacement, content)
    
    content = content.replace(
        'fact = brain_service.create_fact(',
        'fact = await brain_service.create_fact('
    )
    
    # 8. Update /brain/entities/{entity_id}/facts GET - add brain_service dependency
    get_facts_pattern = r'(@router\.get\("/brain/entities/\{entity_id\}/facts"\)[\s\S]*?async def get_entity_facts\(\n\s+entity_id: str,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    get_facts_replacement = r'\1brain_service: CompanyBrain = Depends(get_company_brain),\n    \2'
    content = re.sub(get_facts_pattern, get_facts_replacement, content)
    
    content = content.replace(
        'facts = brain_service.get_entity_facts(entity_id, user=current_user)',
        'facts = await brain_service.get_entity_facts(entity_id, user=current_user)'
    )
    
    # 9. Update /memories POST - add memory_service dependency
    store_memory_pattern = r'(@router\.post\("/memories"\)[\s\S]*?async def store_memory\(\n\s+request: StoreMemoryRequest,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    store_memory_replacement = r'\1memory_service: MemoryService = Depends(get_memory_service),\n    \2'
    content = re.sub(store_memory_pattern, store_memory_replacement, content)
    
    content = content.replace(
        'memory = memory_service.store(',
        'memory = await memory_service.store('
    )
    
    # 10. Update /memories GET - add memory_service dependency
    list_memories_pattern = r'(@router\.get\("/memories"\)[\s\S]*?async def list_memories\(\n\s+memory_type: Optional\[MemoryType\] = Query\(None\),\n\s+)(current_user: User = Depends\(get_current_user\),)'
    list_memories_replacement = r'\1memory_service: MemoryService = Depends(get_memory_service),\n    \2'
    content = re.sub(list_memories_pattern, list_memories_replacement, content)
    
    content = content.replace(
        'memories = memory_service.list_memories(',
        'memories = await memory_service.list_memories('
    )
    
    # 11. Update /memories/{memory_id} DELETE - add memory_service dependency
    delete_memory_pattern = r'(@router\.delete\("/memories/\{memory_id\}"\)[\s\S]*?async def delete_memory\(\n\s+memory_id: str,\n\s+)(current_user: User = Depends\(get_current_user\),)'
    delete_memory_replacement = r'\1memory_service: MemoryService = Depends(get_memory_service),\n    \2'
    content = re.sub(delete_memory_pattern, delete_memory_replacement, content)
    
    content = content.replace(
        'success = memory_service.delete(',
        'success = await memory_service.delete('
    )
    
    # Write updated file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] Knowledge API migrated to database services")
    print("  - Added service factory dependencies")
    print("  - Updated all endpoints to use Depends()")
    print("  - All service calls now async (await)")
    print("  - Removed global service instances")


if __name__ == "__main__":
    migrate_knowledge_api()
