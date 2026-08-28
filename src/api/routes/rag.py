"""
RAG API Routes
Week 4 Day 3 - RAG REST API

提供 RAG 系统的 HTTP 接口
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.identity.models import User
from src.knowledge.vector_store import SQLiteVectorStore
from src.knowledge.rag_pipeline import RAGPipeline

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


# ==================== Pydantic Schemas ====================


class DocumentAddRequest(BaseModel):
    """添加文档请求"""

    text: str = Field(..., min_length=1, description="文档文本")
    metadata: Optional[dict] = Field(None, description="文档元数据")


class DocumentAddResponse(BaseModel):
    """添加文档响应"""

    document_id: str
    text_length: int
    embedding_dim: int


class RAGStatsResponse(BaseModel):
    """RAG 统计响应"""

    status: str
    message: str


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""

    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""

    query: str
    sources: list
    context: str
    answer: str
    metadata: dict


# ==================== API Endpoints ====================

# SQLite-persisted vector store for RAG (survives process restarts)
_vector_store = SQLiteVectorStore()


@router.get("/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
):
    """
    获取 RAG 系统统计信息
    """
    doc_count = len(set(r.document_id for r in _vector_store.records))
    chunk_count = len(_vector_store.records)
    return RAGStatsResponse(
        status="enabled",
        message=f"RAG system active: {doc_count} documents, {chunk_count} chunks",
    )


@router.post("/documents", response_model=DocumentAddResponse)
async def add_document(
    request: DocumentAddRequest,
    current_user: User = Depends(get_current_user),
):
    """
    添加文档到 RAG 知识库
    """
    import uuid
    from src.knowledge.embedding import EmbeddingService

    doc_id = str(uuid.uuid4())
    embed_service = EmbeddingService(provider_name="mock")

    # Generate embedding
    vector = await embed_service.embed_text(request.text)

    # Store in vector store
    _vector_store.insert(
        document_id=doc_id,
        chunk_id=f"{doc_id}-chunk-0",
        content=request.text,
        embedding=vector,
        metadata=request.metadata or {},
    )

    logger.info(
        "rag_document_added",
        document_id=doc_id,
        text_length=len(request.text),
        user_id=current_user.id,
    )

    return DocumentAddResponse(
        document_id=doc_id,
        text_length=len(request.text),
        embedding_dim=len(vector),
    )


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    执行 RAG 查询：检索相关文档并用 LLM 生成回答
    """
    pipeline = RAGPipeline(_vector_store, provider_name="mock")
    result = await pipeline.query(request.query, limit=request.limit)

    return RAGQueryResponse(
        query=result["query"],
        sources=result["sources"],
        context=result["context"],
        answer=result["answer"],
        metadata=result["metadata"],
    )