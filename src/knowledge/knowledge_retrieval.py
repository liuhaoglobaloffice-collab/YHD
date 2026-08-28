"""
LiuHao AI OS Y1.0
Phase 4 Module 2 — Knowledge Retrieval System

Unified knowledge retrieval across all sources:
- Documents
- Memories
- Company Entities
- Facts
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.errors import PermissionDeniedError, ValidationError
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import RBACService


class KnowledgeSource(str, Enum):
    """Knowledge source type"""

    DOCUMENT = "document"
    MEMORY = "memory"
    ENTITY = "entity"
    FACT = "fact"
    ALL = "all"


class SearchStrategy(str, Enum):
    """Search strategy"""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class KnowledgeQuery:
    """
    Unified knowledge query.

    Supports searching across multiple knowledge sources.
    """

    query: str
    sources: List[KnowledgeSource] = field(default_factory=lambda: [KnowledgeSource.ALL])
    strategy: SearchStrategy = SearchStrategy.HYBRID

    # Filters
    user_id: Optional[str] = None
    entity_type: Optional[str] = None
    memory_type: Optional[str] = None

    # Time range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Pagination
    limit: int = 10
    offset: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeResult:
    """
    Knowledge search result.

    Contains item from any knowledge source with relevance score.
    """

    source: KnowledgeSource
    id: str
    title: str
    content: str
    score: float

    # Source-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Context
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source": self.source.value,
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


@dataclass
class KnowledgeContext:
    """
    Knowledge context for AI Brain.

    Aggregated knowledge from multiple sources for a specific task.
    """

    task: str
    results: List[KnowledgeResult]
    total_sources: int
    query_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task": self.task,
            "results": [r.to_dict() for r in self.results],
            "total_sources": self.total_sources,
            "query_time": self.query_time,
        }

    def get_summary(self) -> str:
        """Get context summary for AI prompt"""
        if not self.results:
            return "No relevant knowledge found."

        summary = f"Found {len(self.results)} relevant knowledge items:\n\n"

        for i, result in enumerate(self.results[:5], 1):  # Top 5
            summary += f"{i}. [{result.source.value}] {result.title}\n"
            summary += f"   {result.content[:200]}...\n\n"

        return summary


class KnowledgeRetrievalService:
    """
    Unified Knowledge Retrieval Service.

    Phase 4 Module 2: Multi-source knowledge search with permission control.

    Architecture:
        API → KnowledgeRetrievalService → [Document/Memory/Entity Repositories]
    """

    def __init__(
        self,
        session,  # AsyncSession
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        self.session = session
        self.rbac = rbac_service
        self.audit = audit_service

    async def search(
        self,
        user: User,
        query: KnowledgeQuery,
    ) -> List[KnowledgeResult]:
        """
        Search across knowledge sources.

        Args:
            user: User performing search
            query: Knowledge query

        Returns:
            List of knowledge results sorted by relevance

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Permission check
        if not await self.rbac.check_permission(user, resource="knowledge", action="read"):
            await self.audit.log_permission_denied(
                session=self.session,
                user_id=user.id,
                action="search_knowledge",
                resource_type="knowledge",
                reason="User lacks KNOWLEDGE_READ permission",
            )
            raise PermissionDeniedError("User lacks KNOWLEDGE_READ permission")

        # Validate query
        if not query.query or len(query.query.strip()) == 0:
            raise ValidationError("Search query cannot be empty")

        results = []

        # Search each source
        sources_to_search = (
            query.sources
            if KnowledgeSource.ALL not in query.sources
            else [
                KnowledgeSource.DOCUMENT,
                KnowledgeSource.MEMORY,
                KnowledgeSource.ENTITY,
            ]
        )

        for source in sources_to_search:
            if source == KnowledgeSource.DOCUMENT:
                doc_results = await self._search_documents(user, query)
                results.extend(doc_results)
            elif source == KnowledgeSource.MEMORY:
                mem_results = await self._search_memories(user, query)
                results.extend(mem_results)
            elif source == KnowledgeSource.ENTITY:
                entity_results = await self._search_entities(user, query)
                results.extend(entity_results)
            elif source == KnowledgeSource.FACT:
                fact_results = await self._search_facts(user, query)
                results.extend(fact_results)

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Apply pagination
        paginated = results[query.offset : query.offset + query.limit]

        # Audit log
        await self.audit.log(
            session=self.session,
            action=AuditAction.READ,
            status="success",
            user_id=user.id,
            resource_type="knowledge",
            details={
                "query": query.query,
                "sources": [s.value for s in sources_to_search],
                "result_count": len(paginated),
            },
        )

        return paginated

    async def _search_documents(
        self,
        user: User,
        query: KnowledgeQuery,
    ) -> List[KnowledgeResult]:
        """Search documents"""
        from ..database.repositories.knowledge import DocumentRepository

        repo = DocumentRepository(self.session)

        # Search documents by title or content
        models = await repo.search_full_text(query.query, limit=100)

        results = []
        query_lower = query.query.lower()

        for model in models:
            # Keyword matching in title and content
            title = model.title or model.filename or ""
            content = model.content or ""
            title_match = query_lower in title.lower()
            content_match = query_lower in content.lower()

            if title_match or content_match:
                score = 0.9 if title_match else 0.5

                results.append(
                    KnowledgeResult(
                        source=KnowledgeSource.DOCUMENT,
                        id=str(model.id),
                        title=title,
                        content=content[:500] if content else "",
                        score=score,
                        metadata={
                            "file_type": model.file_type,
                            "tags": model.tags,
                            "summary": model.summary,
                        },
                        created_at=model.created_at,
                        created_by=str(model.created_by),
                    )
                )

        return results

    async def _search_memories(
        self,
        user: User,
        query: KnowledgeQuery,
    ) -> List[KnowledgeResult]:
        """Search memories"""
        from ..database.repositories.knowledge import MemoryRepository

        repo = MemoryRepository(self.session)

        # Query memories by type or all recent memories
        if query.memory_type:
            models = await repo.list_by_type(query.memory_type, limit=100)
        else:
            models = await repo.list_recent(limit=100)

        results = []
        query_lower = query.query.lower()

        for model in models:
            # Simple keyword matching
            import json

            content_data = json.loads(model.content)
            key = content_data.get("key", "")
            value = str(content_data.get("value", ""))

            if query_lower in key.lower() or query_lower in value.lower():
                score = 0.8 if query_lower in key.lower() else 0.5

                results.append(
                    KnowledgeResult(
                        source=KnowledgeSource.MEMORY,
                        id=str(model.id),
                        title=f"Memory: {key}",
                        content=value,
                        score=score,
                        metadata={
                            "memory_type": model.memory_type,
                            "importance": model.importance,
                        },
                        created_at=model.created_at,
                        created_by=str(model.user_id),
                    )
                )

        return results

    async def _search_entities(
        self,
        user: User,
        query: KnowledgeQuery,
    ) -> List[KnowledgeResult]:
        """Search company entities"""
        from ..database.repositories.knowledge import CompanyBrainEntityRepository

        repo = CompanyBrainEntityRepository(self.session)

        # Query entities by type or search by name
        models = []
        if query.entity_type:
            models = await repo.list_by_type(query.entity_type, limit=100)
        else:
            # When no entity_type specified, search by name
            models = await repo.search_by_name(query.query, limit=100)

        results = []
        query_lower = query.query.lower()

        for model in models:
            # Keyword matching in name and attributes
            name_match = query_lower in model.name.lower()
            attr_match = query_lower in str(model.attributes).lower() if model.attributes else False

            if name_match or attr_match:
                score = 0.9 if name_match else 0.6

                results.append(
                    KnowledgeResult(
                        source=KnowledgeSource.ENTITY,
                        id=str(model.id),
                        title=f"{model.entity_type}: {model.name}",
                        content=str(model.attributes),
                        score=score,
                        metadata={
                            "entity_type": model.entity_type,
                            "attributes": model.attributes,
                        },
                        created_at=model.created_at,
                        created_by=str(model.created_by),
                    )
                )

        return results

    async def _search_facts(
        self,
        user: User,
        query: KnowledgeQuery,
    ) -> List[KnowledgeResult]:
        """Search facts"""
        from ..database.repositories.knowledge import CompanyBrainEntityRepository
        from ..database.repositories.knowledge import CompanyBrainFactRepository

        facts_repo = CompanyBrainFactRepository(self.session)
        entities_repo = CompanyBrainEntityRepository(self.session)

        query_lower = query.query.lower()

        # Strategy 1: Search entities by name, then get facts for matching entities
        entities = await entities_repo.search_by_name(query.query, limit=50)
        seen_fact_ids = set()
        results = []

        for entity in entities:
            facts = await facts_repo.list_by_entity(str(entity.id), active_only=True)

            for fact in facts:
                if fact.id in seen_fact_ids:
                    continue
                seen_fact_ids.add(fact.id)

                if (query_lower in fact.attribute.lower() or
                    query_lower in str(fact.value).lower()):
                    score = min(fact.priority / 100.0 + 0.1, 0.95)

                    results.append(
                        KnowledgeResult(
                            source=KnowledgeSource.FACT,
                            id=str(fact.id),
                            title=f"{entity.name}: {fact.attribute}",
                            content=str(fact.value),
                            score=score,
                            metadata={
                                "entity_id": str(entity.id),
                                "entity_name": entity.name,
                                "attribute": fact.attribute,
                                "priority": fact.priority,
                                "confidence": fact.confidence,
                                "source": fact.source,
                            },
                            created_at=fact.created_at,
                            created_by=str(entity.created_by),
                        )
                    )

        # Strategy 2: Also search all active facts directly by attribute/value
        # This catches cases where the query matches fact content but not entity name
        all_facts = await facts_repo.list_all(limit=200)
        for fact in all_facts:
            if not fact.is_active:
                continue
            if fact.id in seen_fact_ids:
                continue

            if (query_lower in fact.attribute.lower() or
                query_lower in str(fact.value).lower()):
                seen_fact_ids.add(fact.id)

                # Look up the entity name if we can
                entity_name = None
                try:
                    entity = await entities_repo.get_by_id(UUID(fact.entity_id))
                    entity_name = entity.name if entity else None
                except Exception:
                    pass

                score = min(fact.priority / 100.0 + 0.1, 0.95)
                prefix = f"{entity_name}: " if entity_name else ""
                results.append(
                    KnowledgeResult(
                        source=KnowledgeSource.FACT,
                        id=str(fact.id),
                        title=f"{prefix}{fact.attribute}",
                        content=str(fact.value),
                        score=score,
                        metadata={
                            "entity_id": fact.entity_id,
                            "entity_name": entity_name,
                            "attribute": fact.attribute,
                            "priority": fact.priority,
                            "confidence": fact.confidence,
                            "source": fact.source,
                        },
                        created_at=fact.created_at,
                        created_by=fact.created_by,
                    )
                )

        return results

    async def build_context(
        self,
        user: User,
        task: str,
        max_items: int = 10,
    ) -> KnowledgeContext:
        """
        Build knowledge context for AI Brain.

        Args:
            user: User requesting context
            task: Task description
            max_items: Maximum context items

        Returns:
            Knowledge context aggregated from all sources
        """
        import time

        start_time = time.time()

        # Create query from task
        query = KnowledgeQuery(
            query=task,
            sources=[KnowledgeSource.ALL],
            limit=max_items,
        )

        # Search
        results = await self.search(user, query)

        query_time = time.time() - start_time

        context = KnowledgeContext(
            task=task,
            results=results,
            total_sources=len(results),
            query_time=query_time,
        )

        # Audit context building
        await self.audit.log(
            session=self.session,
            action=AuditAction.READ,
            status="success",
            user_id=user.id,
            resource_type="knowledge_context",
            details={
                "task": task,
                "items": len(results),
                "query_time": query_time,
            },
        )

        return context
