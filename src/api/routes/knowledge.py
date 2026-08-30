"""
Knowledge API Routes
Stage 4: Document management, search, company brain, and memory

Phase 2F-2 Update: Added database dependency for future Phase 2G migration.
Current implementation still uses memory storage - will be migrated in Phase 2G.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.approval import require_approval_for
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.api.factories.knowledge import (
    get_company_brain,
    get_document_service,
    get_knowledge_retrieval,
    get_memory_service,
)
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.knowledge.company_brain import CompanyBrain, EntityType
from src.knowledge.documents import DocumentService, DocumentType
from src.knowledge.knowledge_retrieval import (
    KnowledgeQuery,
    KnowledgeRetrievalService,
    KnowledgeSource,
    SearchStrategy,
)
from src.knowledge.memory import MemoryService, MemoryType
from src.knowledge.processing import DocumentProcessor
from src.knowledge.retrieval import RetrievalService
from src.knowledge.rag_pipeline import RAGPipeline
from src.knowledge.retriever import Retriever
from src.knowledge.vector_store import InMemoryVectorStore, SQLiteVectorStore

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# Request/Response Models


class DocumentUploadResponse(BaseModel):
    """Document upload response"""

    document_id: UUID
    title: str
    type: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    """Document list response"""

    documents: list[Dict[str, Any]]
    total: int


class SearchRequest(BaseModel):
    """Search request"""

    query: str = Field(..., min_length=1, max_length=500)
    document_id: Optional[UUID] = None
    document_type: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


class SearchResponse(BaseModel):
    """Search response"""

    results: list[Dict[str, Any]]
    total: int


class EntityCreateRequest(BaseModel):
    """Entity creation request"""

    name: str = Field(..., min_length=1, max_length=200)
    entity_type: str
    metadata: Optional[Dict[str, Any]] = None


class EntityResponse(BaseModel):
    """Entity response"""

    entity_id: UUID
    name: str
    entity_type: str
    metadata: Dict[str, Any]
    created_at: str


class FactCreateRequest(BaseModel):
    """Fact creation request"""

    entity_id: UUID
    attribute: str = Field(..., min_length=1, max_length=200)
    value: Any
    priority: int = Field(default=1, ge=1, le=10)
    source: Optional[str] = None


class FactResponse(BaseModel):
    """Fact response"""

    fact_id: UUID
    entity_id: UUID
    attribute: str
    value: Any
    priority: int
    source: Optional[str]
    created_at: str


class MemoryCreateRequest(BaseModel):
    """Memory creation request"""

    memory_type: str
    content: str = Field(..., min_length=1)
    session_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    """Memory response"""

    memory_id: UUID
    memory_type: str
    content: str
    session_id: Optional[UUID]
    task_id: Optional[UUID]
    created_at: str


class RAGSearchRequest(BaseModel):
    """Minimal RAG search request for Phase 2.3."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class RAGQueryRequest(BaseModel):
    """Minimal RAG query/update request shape used by the phase 2.3 API."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class RAGStructuredResponse(BaseModel):
    """Structured RAG answer response contract."""

    query: str
    sources: List[Dict[str, Any]]
    context: str
    answer: str
    metadata: Dict[str, Any]


# Phase 4 Module 2: Knowledge Retrieval models


class KnowledgeSearchRequest(BaseModel):
    """Knowledge search request"""

    query: str = Field(..., min_length=1, max_length=500)
    sources: List[str] = Field(default_factory=lambda: ["documents", "memory"])
    strategy: str = "hybrid"
    entity_type: Optional[str] = None
    memory_type: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class KnowledgeSearchResult(BaseModel):
    """A single knowledge search result."""

    source: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "content": self.content, "score": self.score, "metadata": self.metadata}


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search response"""

    results: List[KnowledgeSearchResult]
    total: int
    sources_searched: List[str]


class KnowledgeContextRequest(BaseModel):
    """Knowledge context request"""

    task: str = Field(..., min_length=1, max_length=500)
    max_items: int = Field(default=5, ge=1, le=20)


class KnowledgeContextResult(BaseModel):
    """A single context result."""

    source: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "content": self.content, "score": self.score, "metadata": self.metadata}


class KnowledgeContext(BaseModel):
    """Knowledge context"""

    task: str
    results: List[KnowledgeContextResult]
    total_sources: int
    query_time: float

    def get_summary(self) -> str:
        return f"Found {self.total_sources} sources for task '{self.task}' in {self.query_time:.2f}s"


class KnowledgeContextResponse(BaseModel):
    """Knowledge context response"""

    task: str
    results: List[KnowledgeContextResult]
    total_sources: int
    query_time: float
    summary: str


# Phase 4: Services now use dependency injection via factories
# processor is lightweight; retrieval_service is lazily created via factory
processor = DocumentProcessor()
retrieval_service = None  # Initialized lazily via get_knowledge_retrieval dependency


# Phase 2.3 RAG lightweight endpoints


@router.post("/search", response_model=RAGStructuredResponse)
async def knowledge_search_route(
    request: RAGSearchRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """Vector search adapter endpoint for the Phase 2.3 RAG interface."""

    store = SQLiteVectorStore()
    retriever = Retriever(store, provider_name="mock")
    hits = await retriever.search(request.query, limit=request.limit)
    return {
        "query": request.query,
        "sources": hits,
        "context": retriever.assemble_context(hits),
        "answer": "",
        "metadata": {"provider": "mock", "retrieval": "vector_similarity"},
    }


@router.post("/query", response_model=RAGStructuredResponse)
async def knowledge_query_route(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """RAG query endpoint that returns the requested output shape."""

    store = SQLiteVectorStore()
    pipeline = RAGPipeline(store, provider_name="mock")
    result = await pipeline.query(request.query, limit=request.limit)
    return result


# Phase 4 Module 2: Knowledge Retrieval endpoints


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


# Document endpoints


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """
    Upload and process a document

    Requires: KNOWLEDGE_WRITE permission
    """
    try:
        # Read file content
        content = await file.read()

        # Detect document type
        filename = file.filename or "document.txt"
        if filename.endswith(".pdf"):
            doc_type = DocumentType.PDF
        elif filename.endswith((".doc", ".docx")):
            doc_type = DocumentType.DOCX
        elif filename.endswith((".xls", ".xlsx")):
            doc_type = DocumentType.XLSX
        elif filename.endswith(".md"):
            doc_type = DocumentType.MARKDOWN
        else:
            doc_type = DocumentType.TEXT

        # Use filename as title if not provided
        if not title:
            title = filename

        # Store document
        doc = await doc_service.create_document(
            title=title,
            content=content,
            doc_type=doc_type,
            metadata={"filename": filename, "uploader_id": str(current_user.id)},
            user=current_user,
        )

        # Process document into chunks
        chunks = processor.process_document(doc)

        # Index chunks for search
        retrieval_service.index_chunks(chunks)

        # Audit: Document uploaded
        await AuditService.log(
            session=session,
            action=AuditAction.DOCUMENT_UPLOADED,
            resource_type="document",
            resource_id=str(doc.id),
            status="success",
            user_id=current_user.id,
            details={"title": title, "type": doc_type.value, "chunk_count": len(chunks)},
        )

        logger.info(
            "document_uploaded",
            document_id=doc.id,
            title=title,
            type=doc_type.value,
            chunk_count=len(chunks),
            user_id=current_user.id,
        )

        return DocumentUploadResponse(
            document_id=doc.id,
            title=doc.title,
            type=doc.type.value,
            chunk_count=len(chunks),
        )

    except Exception as e:
        logger.error("document_upload_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    doc_type: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    List documents

    Requires: KNOWLEDGE_READ permission
    """
    try:
        docs = await doc_service.list_documents(
            user=current_user,
            doc_type=DocumentType(doc_type) if doc_type else None,
            limit=limit,
        )

        return DocumentListResponse(
            documents=[doc.to_dict() for doc in docs],
            total=len(docs),
        )

    except Exception as e:
        logger.error("document_list_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@router.post("/documents/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    Search documents

    Requires: KNOWLEDGE_READ permission
    """
    try:
        results = retrieval_service.search(
            query=request.query,
            user=current_user,
            document_id=request.document_id,
            document_type=request.document_type,
            limit=request.limit,
        )

        logger.info(
            "search_executed",
            query=request.query,
            result_count=len(results),
            user_id=current_user.id,
        )

        return SearchResponse(
            results=[r.to_dict() for r in results],
            total=len(results),
        )

    except Exception as e:
        logger.error("search_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Company Brain endpoints


@router.post("/company-brain/entities", response_model=EntityResponse)
async def create_entity(
    request: EntityCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    brain_service: CompanyBrain = Depends(get_company_brain),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """
    Create a company entity

    Requires: KNOWLEDGE_WRITE permission
    """
    try:
        entity = await brain_service.create_entity(
            user=current_user,
            entity_type=EntityType(request.entity_type),
            name=request.name,
            attributes=request.metadata or {},
        )

        logger.info(
            "entity_created",
            entity_id=entity.id,
            name=entity.name,
            type=entity.entity_type.value,
            user_id=current_user.id,
        )

        return EntityResponse(
            entity_id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type.value,
            metadata=entity.attributes,
            created_at=entity.created_at.isoformat(),
        )

    except Exception as e:
        logger.error("entity_creation_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Entity creation failed: {str(e)}")


@router.get("/company-brain/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    brain_service: CompanyBrain = Depends(get_company_brain),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    Get entity by ID

    Requires: KNOWLEDGE_READ permission
    """
    try:
        entity = await brain_service.get_entity(user=current_user, entity_id=str(entity_id))

        return EntityResponse(
            entity_id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type.value,
            metadata=entity.attributes,
            created_at=entity.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_entity_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Get entity failed: {str(e)}")


@router.post("/company-brain/facts", response_model=FactResponse)
async def create_fact(
    request: FactCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    brain_service: CompanyBrain = Depends(get_company_brain),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """
    Create a fact about an entity

    Requires: KNOWLEDGE_WRITE permission
    """
    try:
        from src.knowledge.company_brain import FactPriority

        # Map 1-10 scale to FactPriority enum values: 10,20,40,60,80,100
        _PRIORITY_MAP = {1: 10, 2: 10, 3: 20, 4: 20, 5: 40, 6: 40, 7: 60, 8: 80, 9: 80, 10: 100}
        fact = await brain_service.create_fact(
            user=current_user,
            entity_id=str(request.entity_id),
            attribute=request.attribute,
            value=request.value,
            source=request.source or "api",
            priority=FactPriority(_PRIORITY_MAP.get(request.priority, 20)),
        )

        logger.info(
            "fact_created",
            fact_id=fact.id,
            entity_id=fact.entity_id,
            attribute=fact.attribute,
            user_id=current_user.id,
        )

        return FactResponse(
            fact_id=fact.id,
            entity_id=fact.entity_id,
            attribute=fact.attribute,
            value=fact.value,
            priority=fact.priority,
            source=fact.source,
            created_at=fact.created_at.isoformat(),
        )

    except Exception as e:
        logger.error("fact_creation_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Fact creation failed: {str(e)}")


@router.get("/company-brain/entities/{entity_id}/facts")
async def get_entity_facts(
    entity_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    brain_service: CompanyBrain = Depends(get_company_brain),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    Get all facts for an entity

    Requires: KNOWLEDGE_READ permission
    """
    try:
        facts = await brain_service.get_entity_facts(user=current_user, entity_id=str(entity_id))

        return {
            "entity_id": str(entity_id),
            "facts": [f.to_dict() for f in facts],
            "total": len(facts),
        }

    except Exception as e:
        logger.error("get_entity_facts_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Get facts failed: {str(e)}")


# Memory endpoints


@router.post("/memory", response_model=MemoryResponse)
async def store_memory(
    request: MemoryCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    _: None = Depends(require_permission("knowledge", "write")),
):
    """
    Store a memory

    Requires: KNOWLEDGE_WRITE permission
    """
    try:
        # Use first 50 chars of content as key, full content as value
        key = request.content[:50]
        memory = await memory_service.store(
            user=current_user,
            memory_type=MemoryType(request.memory_type),
            key=key,
            value=request.content,
            session_id=str(request.session_id) if request.session_id else None,
            task_id=str(request.task_id) if request.task_id else None,
            metadata=request.metadata or {},
        )

        # Audit: Memory stored
        await AuditService.log(
            session=session,
            action=AuditAction.MEMORY_STORED,
            resource_type="memory",
            resource_id=str(memory.id),
            status="success",
            user_id=current_user.id,
            details={"memory_type": memory.memory_type.value},
        )

        logger.info(
            "memory_stored",
            memory_id=memory.id,
            memory_type=memory.memory_type.value,
            user_id=current_user.id,
        )

        return MemoryResponse(
            memory_id=memory.id,
            memory_type=memory.memory_type.value,
            content=memory.value,
            session_id=memory.session_id,
            task_id=memory.task_id,
            created_at=memory.created_at.isoformat(),
        )

    except Exception as e:
        logger.error("memory_storage_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Memory storage failed: {str(e)}")


@router.get("/memory")
async def list_memories(
    memory_type: Optional[str] = None,
    session_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    _: None = Depends(require_permission("knowledge", "read")),
):
    """
    List memories

    Requires: KNOWLEDGE_READ permission
    """
    try:
        memories = await memory_service.list_memories(
            user=current_user,
            memory_type=MemoryType(memory_type) if memory_type else None,
            session_id=str(session_id) if session_id else None,
            task_id=str(task_id) if task_id else None,
        )
        # Apply limit client-side
        memories = memories[:limit]

        return {
            "memories": [m.to_dict() for m in memories],
            "total": len(memories),
        }

    except Exception as e:
        logger.error("memory_list_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Memory list failed: {str(e)}")


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    _: None = Depends(require_permission("knowledge", "delete")),
    _approval: None = Depends(require_approval_for("memory", "delete")),
):
    """
    Delete a memory

    Requires: KNOWLEDGE_DELETE permission
    Phase 2 Governance: Approval required for delete operations.
    """
    try:
        await memory_service.delete(
            user=current_user,
            memory_id=str(memory_id),
        )

        # MemoryService.delete() raises NotFoundError if not found

        # Audit: Memory deleted
        await AuditService.log(
            session=session,
            action=AuditAction.MEMORY_RETRIEVED,
            resource_type="memory",
            resource_id=str(memory_id),
            status="success",
            user_id=current_user.id,
            details={"action": "delete"},
        )

        logger.info(
            "memory_deleted",
            memory_id=memory_id,
            user_id=current_user.id,
        )

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_deletion_failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Memory deletion failed: {str(e)}")
