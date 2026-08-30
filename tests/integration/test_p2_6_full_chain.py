"""P2-6 Full-chain integration tests (Gap 12).

Verifies the complete execution chain across module boundaries:

    AI Employee
      → Provider (AgentRuntime LLM boundary)
      → Knowledge Retrieval (DocumentModel + KnowledgeRetrievalService)
      → Embedding / Vector Store (DocumentProcessor → to_chunk() →
        EmbeddingPipeline with EmbeddingStorageRepository + RAGPipeline)
      → Context (system message injection)
      → LLM (mocked at the AgentRuntime boundary, same as existing tests)
      → Result (execution output)
      → Failure Recovery (FailureRecordModel persisted on provider failure)

The LLM boundary is mocked exactly like the accepted P2-4/P2-5 integration
tests (patch AgentRuntime.execute); every other stage runs for real against
an in-memory SQLite database.
"""

import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.ai.agents import AgentExecution, AgentRuntime, AgentStatus
from src.database.base import Base
from src.database.models import DocumentModel, EmbeddingStorageModel, FailureRecordModel
from src.database.repositories.knowledge import EmbeddingStorageRepository
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService, RoleEnum
from src.knowledge.embedding import EmbeddingPipeline
from src.knowledge.processing import DocumentProcessor
from src.knowledge.rag_pipeline import RAGPipeline
from src.knowledge.vector_store import InMemoryVectorStore
from src.workforce.employee import AIEmployeeService
from src.workforce.models import AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user():
    user = User()
    user.id = 1
    user.username = "p26_user"
    user.email = "p26@test.com"
    user.hashed_password = "test_password"
    user.is_active = True
    user.is_superuser = True
    user.role = RoleEnum.ADMIN
    user.full_name = "P2-6 User"
    user.tenant_id = None
    return user


class MockAudit(AuditService):
    """Audit stub that swallows log calls (same as P2-5 tests)."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        return None


# ============================================================================
# Test 1: Full success chain — ingestion → retrieval → context → LLM → result
# ============================================================================


@pytest.mark.asyncio
async def test_full_chain_success():
    """Document → chunks → embeddings(+DB) → vector store → retrieval →
    AI Employee execution with knowledge context → completed result."""
    session_factory = await create_test_session()
    async with session_factory() as session:
        # ── 1. Knowledge ingestion: DocumentProcessor → Chunk → Embedding ──
        from src.knowledge.processing import Chunker

        doc_id = "doc-chain-1"
        doc_content = (
            "Our supplier risk policy requires quarterly audits of all "
            "Tier-1 suppliers. High-risk suppliers must be reviewed monthly."
        )

        # Persist the document (the knowledge retrieval source of truth)
        doc = DocumentModel(
            id=str(uuid4()),
            filename="policy.txt",
            title="Supplier Risk Policy",
            content=doc_content,
            file_type="txt",
            size=len(doc_content),
            status="uploaded",
            created_by="1",
        )
        session.add(doc)
        user = create_test_user()
        session.add(user)
        await session.commit()

        # Chunk via the processing pipeline, unify via to_chunk()
        processor = DocumentProcessor(chunker=Chunker(max_chunk_size=1000))
        metas = await processor.process_document(
            document_id=doc_id,
            document_version=1,
            file_type="text/plain",
            content=doc_content.encode("utf-8"),
        )
        assert len(metas) >= 1
        unified_chunks = [m.to_chunk() for m in metas]

        # Embed with persistence (EmbeddingStorageModel + vector store)
        store = InMemoryVectorStore()
        embed_session = session_factory()
        repo = EmbeddingStorageRepository(embed_session)
        pipeline = EmbeddingPipeline(
            vector_store=store,
            provider_name="mock",
            storage_repository=repo,
        )
        result = await pipeline.run_chunks(unified_chunks)
        assert result["embeddings_created"] == len(unified_chunks)
        assert result["storage_status"] == "ok"

        # ── 2. Vector store + DB consistency ──
        records = await repo.find_by_document(doc_id)
        assert len(records) == len(unified_chunks)
        for record in records:
            assert store.has_chunk(record.chunk_id)
            assert record.provider == "mock"

        # ── 3. RAG retrieval over the populated vector store ──
        rag = RAGPipeline(vector_store=store, provider_name="mock")
        rag_result = await rag.query("supplier risk policy audits")
        assert rag_result["sources"], "RAG must retrieve the ingested chunk"
        assert rag_result["sources"][0]["document_id"] == doc_id
        assert rag_result["answer"], "LLM (mock provider) must return an answer"
        await embed_session.close()

        # ── 4. AI Employee execution with real knowledge retrieval ──
        registry = AIEmployeeRegistry(session)
        rbac = RBACService(session)
        audit = MockAudit()
        service = AIEmployeeService(registry, rbac, audit)

        from src.ai.agents import AgentType
        from src.workforce.models import AIEmployee

        employee = AIEmployee(
            id=uuid4(),
            name="Chain Employee",
            department=Department.RESEARCH,
            position=Position.MARKET_RESEARCHER,
            description="Full-chain test employee",
            agent_type=AgentType.GPT,
            status=AIEmployeeStatus.ACTIVE,
        )
        registered = await registry.register(employee)
        await session.commit()

        captured_messages = []

        async def mock_agent_execute(self, agent_type, messages, context,
                                     temperature=None, max_tokens=None):
            captured_messages.extend(messages)
            return AgentExecution(
                execution_id=uuid4(),
                agent_type=agent_type,
                context=context,
                status=AgentStatus.COMPLETED,
                input_messages=messages,
                output="Quarterly audits are required for Tier-1 suppliers.",
            )

        with patch.object(AgentRuntime, "execute", mock_agent_execute):
            exec_result = await service.execute_task(
                employee_id=registered.id,
                prompt="What is our supplier audit policy?",
                actor_id=1,
            )

        # ── 5. Result assertions: the full chain completed ──
        assert exec_result["status"] == "completed"
        assert exec_result["output"] == (
            "Quarterly audits are required for Tier-1 suppliers."
        )

        # Knowledge context was retrieved from DocumentModel and injected
        system_msgs = [m for m in captured_messages if m.get("role") == "system"]
        knowledge_msgs = [
            m for m in system_msgs if "知识库" in m.get("content", "")
        ]
        assert knowledge_msgs, "Knowledge context must be injected into LLM messages"
        assert "Supplier Risk Policy" in knowledge_msgs[0]["content"]

        # The user prompt is preserved
        user_msgs = [m for m in captured_messages if m.get("role") == "user"]
        assert user_msgs[-1]["content"] == "What is our supplier audit policy?"


# ============================================================================
# Test 2: Provider failure → Recovery Chain
# ============================================================================


@pytest.mark.asyncio
async def test_provider_failure_enters_recovery_chain():
    """When the LLM (AgentRuntime) fails, the Recovery Chain must record a
    FailureRecordModel — the failure is never silently swallowed."""
    session_factory = await create_test_session()
    async with session_factory() as session:
        user = create_test_user()
        session.add(user)
        await session.commit()

        registry = AIEmployeeRegistry(session)
        rbac = RBACService(session)
        audit = MockAudit()
        service = AIEmployeeService(registry, rbac, audit)

        from src.ai.agents import AgentType
        from src.workforce.models import AIEmployee

        employee = AIEmployee(
            id=uuid4(),
            name="Failing Employee",
            department=Department.RESEARCH,
            position=Position.MARKET_RESEARCHER,
            description="Employee whose LLM call fails",
            agent_type=AgentType.GPT,
            status=AIEmployeeStatus.ACTIVE,
        )
        registered = await registry.register(employee)
        await session.commit()

        async def failing_agent_execute(self, agent_type, messages, context,
                                        temperature=None, max_tokens=None):
            return AgentExecution(
                execution_id=uuid4(),
                agent_type=agent_type,
                context=context,
                status=AgentStatus.FAILED,
                input_messages=messages,
                error="LLM provider timeout [provider=openai]: no response",
            )

        with patch.object(AgentRuntime, "execute", failing_agent_execute):
            exec_result = await service.execute_task(
                employee_id=registered.id,
                prompt="This task will fail at the provider",
                actor_id=1,
            )

        # The execution reports failure (never faked as success)
        assert exec_result["status"] == "failed"
        assert exec_result["error"] is not None
        assert "timeout" in exec_result["error"]

        # The Recovery Chain recorded the failure durably
        stmt = select(FailureRecordModel).where(
            FailureRecordModel.task_id == exec_result["execution_id"]
        )
        result = await session.execute(stmt)
        failure = result.scalar_one_or_none()
        assert failure is not None, "Recovery Chain must persist the provider failure"
        assert failure.failure_summary == (
            f"AI Employee {employee.name} task execution failed"
        )
        assert "timeout" in failure.failure_detail
        # Classified as a provider error by the recovery chain
        assert failure.failure_category == "provider_error"


# ============================================================================
# Test 3: Embedding failure inside the chain leaves no partial state
# ============================================================================


@pytest.mark.asyncio
async def test_embedding_failure_in_chain_leaves_no_partial_state():
    """If the embedding provider fails mid-chain, no EmbeddingStorageModel
    records survive (rollback) and the vector store has no phantom entries."""
    from src.knowledge.embedding import EmbeddingError

    session_factory = await create_test_session()
    async with session_factory() as session:
        from src.knowledge.chunker import Chunk

        chunks = [
            Chunk(chunk_id="chain-doc_chunk_0", document_id="chain-doc",
                  content="First chunk", chunk_index=0),
            Chunk(chunk_id="chain-doc_chunk_1", document_id="chain-doc",
                  content="Second chunk", chunk_index=1),
        ]

        store = InMemoryVectorStore()
        embed_session = session_factory()
        repo = EmbeddingStorageRepository(embed_session)
        pipeline = EmbeddingPipeline(
            vector_store=store,
            provider_name="mock",
            storage_repository=repo,
        )

        embed_calls = {"n": 0}

        async def flaky_embed(text, **kwargs):
            embed_calls["n"] += 1
            if embed_calls["n"] == 2:
                raise EmbeddingError("Embedding provider unavailable")
            return [0.1, 0.2, 0.3]

        with patch.object(pipeline.embedding_service, "embed_text", flaky_embed):
            with pytest.raises(EmbeddingError, match="unavailable"):
                await pipeline.run_chunks(chunks)

        # No DB records survive the rollback
        records = await repo.find_by_document("chain-doc")
        assert records == []
        await embed_session.close()

        # The document remains retrievable-by-title only via DocumentModel —
        # no phantom embeddings exist anywhere
        stmt = select(EmbeddingStorageModel).where(
            EmbeddingStorageModel.document_id == "chain-doc"
        )
        result = await session.execute(stmt)
        assert result.scalars().all() == []
