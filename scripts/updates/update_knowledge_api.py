#!/usr/bin/env python3
"""Update knowledge.py to add Phase 4 Module 2 endpoints"""

# Read current knowledge.py
with open('src/api/routes/knowledge.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add new models after MemoryResponse
models_to_add = """


class KnowledgeSearchRequest(BaseModel):
    \"\"\"Knowledge search request (Phase 4 Module 2)\"\"\"
    query: str = Field(..., min_length=1, max_length=500)
    sources: list[str] = Field(default=["all"])
    strategy: str = Field(default="hybrid")
    entity_type: Optional[str] = None
    memory_type: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class KnowledgeSearchResponse(BaseModel):
    \"\"\"Knowledge search response\"\"\"
    results: list[Dict[str, Any]]
    total: int
    sources_searched: list[str]


class KnowledgeContextRequest(BaseModel):
    \"\"\"Knowledge context request for AI Brain\"\"\"
    task: str = Field(..., min_length=1, max_length=1000)
    max_items: int = Field(default=10, ge=1, le=20)


class KnowledgeContextResponse(BaseModel):
    \"\"\"Knowledge context response\"\"\"
    task: str
    results: list[Dict[str, Any]]
    total_sources: int
    query_time: float
    summary: str
"""

# Find the line after MemoryResponse
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'class MemoryResponse' in line:
        # Find the end of this class
        for j in range(i+1, len(lines)):
            if lines[j].strip() == 'created_at: str':
                # Insert after this line
                lines.insert(j+1, models_to_add)
                break
        break

content = '\n'.join(lines)

# 2. Add new endpoints before "# Document endpoints"
endpoints_to_add = """

# Phase 4 Module 2: Knowledge Retrieval endpoints

@router.post("/retrieval/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: KnowledgeRetrievalService = Depends(get_knowledge_retrieval),
    _: None = Depends(require_permission("knowledge", "read")),
):
    \"\"\"
    Unified knowledge search across all sources.
    
    Phase 4 Module 2: Multi-source knowledge retrieval.
    
    Requires: KNOWLEDGE_READ permission
    \"\"\"
    try:
        # Convert request to KnowledgeQuery
        query = KnowledgeQuery(
            query=request.query,
            sources=[KnowledgeSource(s) for s in request.sources],
            strategy=SearchStrategy(request.strategy),
            entity_type=request.entity_type,
            memory_type=request.memory_type,
            limit=request.limit,
            offset=request.offset,
        )
        
        # Execute search
        results = await retrieval_service.search(current_user, query)
        
        logger.info(
            "knowledge_search_executed",
            query=request.query,
            sources=request.sources,
            result_count=len(results),
            user_id=current_user.id,
        )
        
        return KnowledgeSearchResponse(
            results=[r.to_dict() for r in results],
            total=len(results),
            sources_searched=request.sources,
        )
        
    except Exception as e:
        logger.error("knowledge_search_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {str(e)}")


@router.post("/retrieval/context", response_model=KnowledgeContextResponse)
async def build_knowledge_context(
    request: KnowledgeContextRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: KnowledgeRetrievalService = Depends(get_knowledge_retrieval),
    _: None = Depends(require_permission("knowledge", "read")),
):
    \"\"\"
    Build knowledge context for AI Brain task execution.
    
    Phase 4 Module 2: Context builder for AI task planning.
    
    Requires: KNOWLEDGE_READ permission
    \"\"\"
    try:
        # Build context
        context = await retrieval_service.build_context(
            user=current_user,
            task=request.task,
            max_items=request.max_items,
        )
        
        logger.info(
            "knowledge_context_built",
            task=request.task,
            total_sources=context.total_sources,
            query_time=context.query_time,
            user_id=current_user.id,
        )
        
        return KnowledgeContextResponse(
            task=context.task,
            results=[r.to_dict() for r in context.results],
            total_sources=context.total_sources,
            query_time=context.query_time,
            summary=context.get_summary(),
        )
        
    except Exception as e:
        logger.error("knowledge_context_build_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Context build failed: {str(e)}")

"""

content = content.replace('# Document endpoints', endpoints_to_add + '\n# Document endpoints')

# 3. Add dependency injection to existing endpoints
# Add doc_service parameter to upload_document
content = content.replace(
    'async def upload_document(\n    file: UploadFile = File(...),\n    title: Optional[str] = None,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "write")),',
    'async def upload_document(\n    file: UploadFile = File(...),\n    title: Optional[str] = None,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    doc_service: DocumentService = Depends(get_document_service),\n    _: None = Depends(require_permission("knowledge", "write")),'
)

# Add doc_service to list_documents
content = content.replace(
    'async def list_documents(\n    doc_type: Optional[str] = None,\n    limit: int = 50,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "read")),',
    'async def list_documents(\n    doc_type: Optional[str] = None,\n    limit: int = 50,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    doc_service: DocumentService = Depends(get_document_service),\n    _: None = Depends(require_permission("knowledge", "read")),'
)

# Add brain_service to create_entity
content = content.replace(
    'async def create_entity(\n    request: EntityCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "write")),',
    'async def create_entity(\n    request: EntityCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    brain_service: CompanyBrain = Depends(get_company_brain),\n    _: None = Depends(require_permission("knowledge", "write")),'
)

# Add brain_service to get_entity
content = content.replace(
    'async def get_entity(\n    entity_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "read")),',
    'async def get_entity(\n    entity_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    brain_service: CompanyBrain = Depends(get_company_brain),\n    _: None = Depends(require_permission("knowledge", "read")),'
)

# Add brain_service to create_fact
content = content.replace(
    'async def create_fact(\n    request: FactCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "write")),',
    'async def create_fact(\n    request: FactCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    brain_service: CompanyBrain = Depends(get_company_brain),\n    _: None = Depends(require_permission("knowledge", "write")),'
)

# Add brain_service to get_entity_facts
content = content.replace(
    'async def get_entity_facts(\n    entity_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "read")),',
    'async def get_entity_facts(\n    entity_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    brain_service: CompanyBrain = Depends(get_company_brain),\n    _: None = Depends(require_permission("knowledge", "read")),'
)

# Add memory_service to store_memory
content = content.replace(
    'async def store_memory(\n    request: MemoryCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "write")),',
    'async def store_memory(\n    request: MemoryCreateRequest,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    memory_service: MemoryService = Depends(get_memory_service),\n    _: None = Depends(require_permission("knowledge", "write")),'
)

# Add memory_service to list_memories
content = content.replace(
    'async def list_memories(\n    memory_type: Optional[str] = None,\n    session_id: Optional[UUID] = None,\n    task_id: Optional[UUID] = None,\n    limit: int = 50,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "read")),',
    'async def list_memories(\n    memory_type: Optional[str] = None,\n    session_id: Optional[UUID] = None,\n    task_id: Optional[UUID] = None,\n    limit: int = 50,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    memory_service: MemoryService = Depends(get_memory_service),\n    _: None = Depends(require_permission("knowledge", "read")),'
)

# Add memory_service to delete_memory
content = content.replace(
    'async def delete_memory(\n    memory_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    _: None = Depends(require_permission("knowledge", "delete")),\n    _approval: None = Depends(require_approval_for("memory", "delete")),',
    'async def delete_memory(\n    memory_id: UUID,\n    session: AsyncSession = Depends(get_db),\n    current_user: User = Depends(get_current_user),\n    memory_service: MemoryService = Depends(get_memory_service),\n    _: None = Depends(require_permission("knowledge", "delete")),\n    _approval: None = Depends(require_approval_for("memory", "delete")),'
)

# Write back
with open('src/api/routes/knowledge.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Successfully updated src/api/routes/knowledge.py")
print("Added:")
print("  - KnowledgeSearchRequest/Response models")
print("  - KnowledgeContextRequest/Response models")
print("  - /retrieval/search endpoint")
print("  - /retrieval/context endpoint")
print("  - Dependency injection for all services")
