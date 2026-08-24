# Phase 4 Module 2 additions to knowledge.py

# Add these models after MemoryResponse:

class KnowledgeSearchRequest(BaseModel):
    """Knowledge search request (Phase 4 Module 2)"""
    query: str = Field(..., min_length=1, max_length=500)
    sources: list[str] = Field(default=["all"])
    strategy: str = Field(default="hybrid")
    entity_type: Optional[str] = None
    memory_type: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search response"""
    results: list[Dict[str, Any]]
    total: int
    sources_searched: list[str]


class KnowledgeContextRequest(BaseModel):
    """Knowledge context request for AI Brain"""
    task: str = Field(..., min_length=1, max_length=1000)
    max_items: int = Field(default=10, ge=1, le=20)


class KnowledgeContextResponse(BaseModel):
    """Knowledge context response"""
    task: str
    results: list[Dict[str, Any]]
    total_sources: int
    query_time: float
    summary: str


# Add these endpoints before "# Document endpoints":

@router.post("/retrieval/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: KnowledgeRetrievalService = Depends(get_knowledge_retrieval),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    Unified knowledge search across all sources.
    
    Phase 4 Module 2: Multi-source knowledge retrieval.
    
    Requires: KNOWLEDGE_READ permission
    """
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
    """
    Build knowledge context for AI Brain task execution.
    
    Phase 4 Module 2: Context builder for AI task planning.
    
    Requires: KNOWLEDGE_READ permission
    """
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
