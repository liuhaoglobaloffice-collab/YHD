"""
RAG API Routes
Week 4 Day 3 - RAG REST API

提供 RAG 系统的 HTTP 接口（临时禁用，等待 Ollama Provider 实现）
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# TODO: Re-enable when Ollama provider is available
# from src.ai.providers.ollama import OllamaProvider, OllamaConfig
# from src.ai.rag import RAGSystem
from src.api.dependencies import get_current_user
from src.identity.models import User

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


# ==================== API Endpoints (Disabled) ====================


@router.get("/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
):
    """
    获取 RAG 系统统计信息

    需要认证（临时禁用）
    """
    return RAGStatsResponse(
        status="disabled",
        message="RAG system is temporarily disabled until Ollama provider is implemented"
    )


@router.post("/documents", status_code=503)
async def add_document_disabled():
    """RAG 文档添加功能已禁用"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="RAG system is temporarily disabled"
    )
