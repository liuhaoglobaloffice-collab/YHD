# P2 Current State Audit Report

> Date: 2026-08-29
> Project: LiuHao AI OS Y1.0
> Phase: P2 READ-ONLY AUDIT

---

## 1. Provider System

### 1.1 Two Parallel Provider Systems

There are **two separate provider abstraction layers** in the codebase:

| System | Interface | Location | Status |
|--------|-----------|----------|--------|
| **New Unified LLMProvider** | `chat()`, `generate()`, `embeddings()` | `src/providers/` | **Partially implemented** |
| **Old ProviderGateway** | `BaseProvider.execute()`, streaming | `src/ai/providers.py` | **Fully implemented, used by AgentRuntime** |

### 1.2 `src/providers/` (New Unified)

| File | Status | Description |
|------|--------|-------------|
| `llm_base.py` | **Complete** | `LLMProvider` ABC with `chat()`, `generate()`, `embeddings()` |
| `base.py` | **Existing** | `RiskAssessmentProvider` (legacy, marked deprecated) |
| `mock.py` | **Complete** | Implements both `RiskAssessmentProvider` + `LLMProvider` |
| `openai.py` | **Complete** | Real OpenAI API calls via httpx |
| `self_host.py` | **Scaffold only** | Returns deterministic mock responses, not real Ollama |
| `registry.py` | **Complete** | `register_provider()` / `get_provider()` with name normalization |
| `__init__.py` | **Complete** | Exports all public symbols |

**Gap:** `self_host.py` does NOT actually connect to Ollama. It returns hardcoded deterministic responses. The `.env` config has `LLM_PROVIDER=ollama` but no code in `src/providers/` reads this.

### 1.3 `src/ai/providers.py` (Old ProviderGateway)

| Provider | Status | Description |
|----------|--------|-------------|
| `BaseProvider` | **Complete** | ABC with `execute()`, streaming, metrics |
| `ProviderGateway` | **Complete** | Singleton, creates providers by `ProviderType` |
| `MockProvider` | **Complete** | Deterministic mock responses |
| `OpenAIProvider` | **Complete** | Real OpenAI API |
| `AnthropicProvider` | **Complete** | Real Anthropic API |
| `GoogleProvider` | **Complete** | Real Google API |
| `GenericHTTPProvider` | **Complete** | Generic HTTP wrapper |
| `XAIProvider` | **Complete** | Extends GenericHTTPProvider |
| `DeepSeekProvider` | **Complete** | Extends GenericHTTPProvider |
| `MoonshotProvider` | **Complete** | Extends GenericHTTPProvider |
| `OllamaProvider` | **Complete** | Real Ollama API via `ollama` Python SDK |

**This system is fully functional** and is used by `AgentRuntime` → `ProviderGateway` → `BaseProvider`.

### 1.4 `src/ai/base.py` (Third Interface)

Another `AIProvider` ABC with `ProviderConfig`. This is a **third** abstraction layer that overlaps with both systems above. It is NOT used by the main call chain.

**Gap:** 3 provider abstractions exist. The `LLMProvider` (`src/providers/`) is not connected to `ProviderGateway` (`src/ai/providers.py`). The `EmbeddingService` uses `LLMProvider` but `AgentRuntime` uses `ProviderGateway`.

### 1.5 Provider Configuration

- `.env` has `LLM_PROVIDER=ollama` and `OLLAMA_ENABLED=true` and `OLLAMA_HOST=http://localhost:11434`
- `OllamaProvider` in `src/ai/providers.py` reads from `SecretsManager` / config object, NOT from `.env` directly
- No code reads `LLM_PROVIDER` env var to configure the new `src/providers/` registry
- API keys are in `.env` (OPENAI_API_KEY, etc.) but mostly empty

### 1.6 Missing: timeout / error handling / unavailable handling

- `BaseProvider.execute()` has try/except for `ExternalServiceError` but no explicit timeout per provider
- `OpenAIProvider` in `src/providers/` sets httpx timeout=60
- No unified provider health check / circuit breaker
- No graceful degradation when provider is unavailable

---

## 2. Knowledge System

### 2.1 Document Management

| Component | Status | Persistence |
|-----------|--------|-------------|
| `DocumentService` | **Complete** (business logic) | **In-memory** `_documents: Dict[str, DocumentMetadata]` |
| `DocumentRepository` | **Complete** (DB queries) | **Database** (SQLAlchemy) |
| `DocumentModel` (DB) | **Complete** | SQLite/PostgreSQL |

**Gap:** `DocumentService.upload_document()` stores metadata in `self._documents` dict (memory only), NOT in the database via `DocumentRepository`. The `DocumentRepository` exists and has full CRUD, but `DocumentService` doesn't use it.

### 2.2 Document Processing

| Component | Status | Description |
|-----------|--------|-------------|
| `DocumentProcessor` | **Complete** | Parses PDF/DOCX/XLSX/TXT/MD, extracts text |
| `Chunker` (processing.py) | **Complete** | Paragraph-based chunking with type detection |
| `TextChunker` (chunker.py) | **Complete** | Simple fixed-size chunking with overlap |
| `ChunkMetadata` | **Complete** | Dataclass for chunk metadata |
| `Chunk` (chunker.py) | **Complete** | Dataclass for new chunk format |

**Gap:** Two chunker implementations exist (`Chunker` in processing.py and `TextChunker` in chunker.py). They produce different chunk types (`ChunkMetadata` vs `Chunk`).

### 2.3 Embedding Pipeline

| Component | Status | Description |
|-----------|--------|-------------|
| `EmbeddingService` | **Complete** | Uses `LLMProvider.embeddings()` via `get_provider()` |
| `EmbeddingPipeline` | **Complete** | Orchestrates chunk → embed → store |
| `InMemoryVectorStore` | **Complete** | List-based, not persistent |
| `SQLiteVectorStore` | **Complete** | SQLite-backed, persistent |
| `DocumentChunkModel` (DB) | **Complete** | Database model for chunks |
| `EmbeddingStorageModel` (DB) | **Complete** | Database model for embeddings |

**Gap:** `EmbeddingPipeline` uses `InMemoryVectorStore` by default. `SQLiteVectorStore` is available but not used as default. `EmbeddingStorageModel` is not used by `EmbeddingPipeline` (it uses vector store directly).

### 2.4 Retrieval

| Component | Status | Description |
|-----------|--------|-------------|
| `RetrievalService` | **Complete** | Hybrid search (keyword + semantic), in-memory chunks |
| `Retriever` | **Complete** | Simple vector search, uses vector store |
| `RAGPipeline` | **Complete** | Full RAG: query → embed → search → LLM → answer |
| `KnowledgeRetrievalService` | **Complete** | Multi-source search (documents, memories, entities, facts) |
| `SearchQuery` / `SearchResult` | **Complete** | Query/result dataclasses |
| `KnowledgeQuery` / `KnowledgeResult` | **Complete** | Unified query/result dataclasses |

**Gap:** `RetrievalService` stores chunks in-memory (`self._chunks: Dict[str, ChunkMetadata]`). `KnowledgeRetrievalService` uses database repositories correctly. Two parallel retrieval systems exist.

### 2.5 Company Brain

| Component | Status | Description |
|-----------|--------|-------------|
| `CompanyBrain` | **Complete** | Entity/fact CRUD via database repositories |
| `Entity` / `Fact` | **Complete** | Dataclasses |
| `CompanyBrainEntityRepository` | **Complete** | DB CRUD + search |
| `CompanyBrainFactRepository` | **Complete** | DB CRUD + conflict resolution |
| `CompanyBrainEntityModel` (DB) | **Complete** | Database model |
| `CompanyBrainFactModel` (DB) | **Complete** | Database model |

**Status:** Company Brain is **fully database-backed** and functional. No significant gaps.

### 2.6 Memory System

| Component | Status | Description |
|-----------|--------|-------------|
| `MemoryService` | **Complete** | Store/retrieve/list/delete via database |
| `MemoryRepository` | **Complete** | DB CRUD + type/recent/important queries |
| `MemoryModel` (DB) | **Complete** | Database model |

**Status:** Memory system is **fully database-backed** and functional.

### 2.7 Security

| Component | Status |
|-----------|--------|
| `KnowledgeSecurityPolicy` | **Complete** |
| `PII detection` | **Complete** |
| RBAC integration | **Complete** |
| Audit logging | **Complete** |

---

## 3. AI Employee → Provider Call Chain

```
AIEmployeeService.execute_task()
  → AgentRuntime.execute()
    → ProviderGateway.get_provider()
      → BaseProvider (OllamaProvider / MockProvider / etc.)
        → execute() → LLM API call
```

**This chain is fully functional.** The ProviderGateway is the central routing point.

**Gap:** The new `LLMProvider` (`src/providers/`) is NOT in this chain. `EmbeddingService` uses `LLMProvider` for embeddings, but `AgentRuntime` uses `ProviderGateway` for chat/generate.

---

## 4. Database Models

### Existing Models

| Model | Table | Status |
|-------|-------|--------|
| `DocumentModel` | `documents` | Complete |
| `DocumentChunkModel` | `document_chunks` | Complete (P2.2) |
| `EmbeddingStorageModel` | `embedding_storage` | Complete (P2.2) |
| `MemoryModel` | `memories` | Complete |
| `CompanyBrainEntityModel` | `company_brain_entities` | Complete |
| `CompanyBrainFactModel` | `company_brain_facts` | Complete |
| `GoalModel` | `goals` | Complete (P1) |
| `FailureRecordModel` | `failure_records` | Complete (P1) |
| `TaskModel` | `tasks` | Complete (P1) |
| `WorkflowModel` | `workflows` | Complete |
| `AIEmployeeModel` | `ai_employees` | Complete |
| `AgentMemoryModel` | `agent_memories` | Complete |

### Foreign Keys

- `DocumentChunkModel.document_id → DocumentModel.id` ✓
- `EmbeddingStorageModel.document_id → DocumentModel.id` ✓
- `CompanyBrainFactModel.entity_id` → (string, no FK constraint) ⚠️
- `FailureRecordModel.goal_id → GoalModel.id` ✓

### Missing / Needed

- **No chunk-to-embedding FK** (`EmbeddingStorageModel.chunk_id` is string, no FK)
- **No document content binary storage** (`DocumentModel.content` stores extracted text, not original file)
- **No DocumentChunkModel → EmbeddingStorageModel link** (they are separate models)

---

## 5. Existing Test Coverage

### Provider Tests
| File | Tests | Status |
|------|-------|--------|
| `tests/providers/test_provider_switching.py` | 1 test | Basic contract check |

### Knowledge Tests
| File | Tests | Status |
|------|-------|--------|
| `tests/knowledge/test_embedding_pipeline_phase22.py` | 4 tests | Chunking, embedding, vector store, pipeline |
| `tests/knowledge/test_knowledge_retrieval.py` | ~5 tests | Document search, fact search, multi-source |
| `tests/knowledge/test_rag_pipeline.py` | ~3 tests | RAG flow |
| `tests/knowledge/test_security_policy.py` | ~3 tests | Security policy |
| `tests/knowledge/test_semantic_search.py` | ~3 tests | Semantic search |

### Missing Tests
- **No test for `DocumentService` with database persistence**
- **No test for `EmbeddingPipeline` with `SQLiteVectorStore`**
- **No test for `RetrievalService` with real database-backed chunks**
- **No test for provider unavailable / timeout / error**
- **No test for Ollama provider integration**
- **No test for duplicate ingestion / failure rollback**
- **No test for `CompanyBrain` update/delete**
- **No test for AI Employee → Provider integration with real ProviderGateway**

---

## 6. Ollama Integration Status

| Check | Result |
|-------|--------|
| `ollama` Python SDK installed | **Yes** (used by `OllamaProvider`) |
| `qwen2.5:3b` model downloaded | **Yes** (1.9 GB, 2 days ago) |
| `qwen2.5:7b` model downloaded | **Yes** (4.7 GB, 2 days ago) |
| `OLLAMA_HOST` configured | `http://localhost:11434` |
| `OLLAMA_ENABLED=true` | **Yes** |
| Ollama service running | **Yes** (confirmed: both models respond to API) |

**Ollama is ready.** No blocking issue. Models are downloaded.

---

## 7. Key Gaps Summary

### Critical (must fix in P2)

| # | Gap | Location |
|---|-----|----------|
| 1 | `DocumentService` stores data in-memory, not database | `src/knowledge/documents.py` |
| 2 | `RetrievalService` stores chunks in-memory, not database | `src/knowledge/retrieval.py` |
| 3 | `LLMProvider` (new) not connected to `ProviderGateway` (old) | `src/providers/` vs `src/ai/providers.py` |
| 4 | `SelfHostProvider` is mock scaffold, doesn't call Ollama | `src/providers/self_host.py` |
| 5 | `EmbeddingPipeline` defaults to `InMemoryVectorStore` | `src/knowledge/embedding.py` |
| 6 | No duplicate ingestion prevention | `src/knowledge/embedding.py` |
| 7 | No failure rollback in embedding pipeline | `src/knowledge/embedding.py` |

### Important (should fix in P2)

| # | Gap | Location |
|---|-----|----------|
| 8 | Missing provider timeout/error/unavailable handling | `src/providers/` |
| 9 | No unified provider health check | All providers |
| 10 | Two chunker implementations with different output types | `processing.py` vs `chunker.py` |
| 11 | `EmbeddingStorageModel` not used by pipeline | `src/knowledge/embedding.py` |
| 12 | Missing tests for persistence, error, rollback | Tests |

### Not Needed (explicitly excluded)

| # | Item | Reason |
|---|------|--------|
| A | Graph DB for Company Brain | Current JSON + SQLite sufficient |
| B | Multi-user SaaS features | Personal + team use only |
| C | Vector DB (PGVector, Qdrant, etc.) | SQLiteVectorStore sufficient for current scope |
| D | Full PDF/image parsing | `DocumentProcessor` handles basic PDF/DOCX/XLSX |
| E | Streaming provider abstraction | `ProviderGateway` already supports streaming |

---

## 8. P2 Recommended Implementation Order

```
Phase 1: P2-1 Unified AI Provider
  - Connect LLMProvider to ProviderGateway (or bridge)
  - Add timeout/error handling to LLMProvider
  - Make SelfHostProvider call real Ollama
  - Wire LLM_PROVIDER env var to provider selection

Phase 2: P2-2 Embedding Pipeline
  - Make DocumentService persist to database (use DocumentRepository)
  - Make EmbeddingPipeline use SQLiteVectorStore by default
  - Add duplicate ingestion prevention
  - Add failure rollback (transactional)

Phase 3: P2-3 Knowledge Retrieval
  - Make RetrievalService use database-backed chunks
  - Or consolidate on KnowledgeRetrievalService (already DB-backed)
  - Ensure semantic retrieval works with real embeddings
  - Add empty knowledge base / provider unavailable handling

Phase 4: P2-4 Company Brain
  - Minimal: verify existing CRUD works
  - Add update/delete tests if missing

Phase 5: P2-5 AI Employee Integration
  - Wire AI Employee → Provider → Knowledge Retrieval → Context → LLM
  - Ensure Provider failure → Recovery Chain
  - Ensure Knowledge failure → proper error (not silent success)
  - Regression test: Audit/Event not bypassed
```

---

## 9. Files That Will Be Modified

| File | Change |
|------|--------|
| `src/providers/self_host.py` | Connect to real Ollama |
| `src/providers/registry.py` | Read LLM_PROVIDER from env |
| `src/providers/llm_base.py` | Add timeout/error handling (minimal) |
| `src/knowledge/documents.py` | Database persistence for DocumentService |
| `src/knowledge/embedding.py` | Default to SQLiteVectorStore, add dedup, rollback |
| `src/knowledge/retrieval.py` | Database-backed chunks (or consolidate) |
| `src/knowledge/company_brain.py` | Minimal: verify update/delete |
| `src/knowledge/__init__.py` | Export updates if needed |
| `src/workforce/employee.py` | Wire knowledge → context → LLM |
| `tests/providers/test_provider_switching.py` | Expand tests |
| `tests/knowledge/test_embedding_pipeline_phase22.py` | Add persistence/rollback tests |
| `tests/knowledge/test_knowledge_retrieval.py` | Add error/empty tests |
| New: `tests/knowledge/test_company_brain.py` | If update/delete tests missing |
| New: `tests/integration/test_ai_employee_provider.py` | Integration test |

## 10. New Database Models Needed

**None.** The existing models (`DocumentModel`, `DocumentChunkModel`, `EmbeddingStorageModel`, `MemoryModel`, `CompanyBrainEntityModel`, `CompanyBrainFactModel`) are sufficient for P2.

## 11. New Dependencies Needed

**None.** All required dependencies are already in the project:
- `httpx` (for OpenAI HTTP calls)
- `ollama` Python SDK (for Ollama)
- `aiosqlite` / `sqlite3` (for vector store)
- `pypdf`, `python-docx`, `openpyxl` (for document parsing)