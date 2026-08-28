"""
Knowledge Layer - Stage 4

Unified Knowledge Base, Company Brain, and Memory System.
"""

from .company_brain import (
    CompanyBrain,
    Entity,
    EntityType,
    Fact,
    FactConfidence,
)
from .documents import (
    DocumentMetadata,
    DocumentService,
    DocumentStatus,
)
from .memory import (
    Memory,
    MemoryService,
    MemoryType,
)
from .processing import (
    Chunker,
    ChunkMetadata,
    DocumentProcessor,
)
from .retrieval import (
    RetrievalService,
    SearchQuery,
    SearchResult,
)
from .chunker import TextChunker, Chunk, chunk_text
from .embedding import EmbeddingService, EmbeddingPipeline
from .vector_store import InMemoryVectorStore, SQLiteVectorStore, VectorRecord
from .retriever import Retriever
from .rag_pipeline import RAGPipeline
from .security import KnowledgeSecurityPolicy, KnowledgeSecurityEvent, validate_user_access
from .pii import detect_pii

__all__ = [
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentService",
    "DocumentProcessor",
    "ChunkMetadata",
    "Chunker",
    "TextChunker",
    "Chunk",
    "chunk_text",
    "EmbeddingService",
    "EmbeddingPipeline",
    "InMemoryVectorStore",
    "SQLiteVectorStore",
    "VectorRecord",
    "Retriever",
    "RAGPipeline",
    "KnowledgeSecurityPolicy",
    "KnowledgeSecurityEvent",
    "validate_user_access",
    "detect_pii",
    "SearchQuery",
    "SearchResult",
    "RetrievalService",
    "EntityType",
    "Entity",
    "Fact",
    "FactConfidence",
    "CompanyBrain",
    "MemoryType",
    "Memory",
    "MemoryService",
]
