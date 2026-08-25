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

__all__ = [
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentService",
    "DocumentProcessor",
    "ChunkMetadata",
    "Chunker",
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
