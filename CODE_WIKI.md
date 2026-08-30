# LiuHao AI OS Code Wiki

> **版本**: Y1.0  
> **定位**: 面向外贸业务的企业级 AI 操作系统原型  
> **更新日期**: 2026-08-30

---

## 目录

1. 项目概述
2. 整体架构
3. 目录结构
4. 后端模块详解
5. 前端模块详解
6. 数据库模型
7. 关键类与函数
8. 依赖关系
9. 核心业务流程
10. 运行与部署
11. 测试体系
12. 安全与治理
13. 配置说明

---

## 1. 项目概述

### 1.1 项目定位

LiuHao AI OS 是一个 **CEO-First** 的企业级 AI 操作系统，专为外贸企业设计。系统以供应商业务闭环为核心，整合 AI 风险评估、任务驱动、工作流编排与审计链路，帮助企业老板实现：

- 一句话目标：自然语言下达经营目标，AI 自动拆解执行
- AI 员工团队：多角色 AI 员工（CEO助理、分析师、研究员、销售等）协同工作
- 供应商风控：AI 驱动的供应商风险评估与预警
- 自主获客：多渠道线索挖掘、CRM 跟进、邮件自动化
- 数据安全：RBAC 权限、审计日志、数据隔离、主/子账号体系

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| 诚实降级 | 无真实 API Key/凭据时，明确返回 MOCK/NOT_CONFIGURED，绝不伪造成功 |
| Fail Closed | 权限策略默认拒绝；未知 Provider 不静默 fallback Mock（生产环境） |
| 持久化优先 | 所有真实执行结果必须落盘（Task/Workflow/Goal/Audit 全程记录） |
| 成本可追溯 | 每次 LLM 调用记录 provider、model、tokens、cost、latency、status |
| 最小侵入 | 优先最小修改，不做大规模重构；不修改已验收的 Failure Recovery Chain |
| 生产安全 | 默认密钥拒绝启动；CORS 从环境变量读取；.env 不进 Docker 镜像 |

### 1.3 技术栈概览

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + Uvicorn + Python 3.10/3.11 |
| 前端框架 | React 18 + Vite + TypeScript + TailwindCSS |
| 数据库 | SQLite（开发）/ PostgreSQL 16（生产），SQLAlchemy 2.0 ORM（异步） |
| ORM 迁移 | Alembic |
| AI Provider | OpenAI / Anthropic / Google / DeepSeek / XAI / Moonshot / Ollama / Mock |
| 嵌入/RAG | 多 Provider Embedding + Hybrid Search（向量+关键词） |
| 认证鉴权 | JWT (python-jose) + Passlib (bcrypt) + RBAC + ABAC |
| 容器化 | Docker + Docker Compose（后端/前端/PostgreSQL 三服务） |
| 前端路由 | React Router v6 |
| UI 组件 | Lucide React 图标 + Storybook 组件库 |
| 测试 | pytest（后端）+ Vitest/Testing Library（前端） |

---

## 2. 整体架构

### 2.1 分层架构图

`
Frontend (React)
    Dashboard / Employees / Workflow / Goals / CRM / Security
             | HTTPS / REST API
             v
FastAPI Application Layer (src/api)
    Routes / Dependencies / Schemas / Lifespan / Factories
             |
             v
Business Service Layer
    GoalService / TaskService / WorkflowService / LeadService
    SupplierRiskAgent / AIEmployeeService / CEO Dashboard
    EmailService / PlatformService / KnowledgeRetrieval
             |
             v
AI Core Engine Layer (src/ai)
    AgentRuntime / ProviderGateway / Planner / GoalService
    Orchestrator / RecoveryChain / RAGPipeline / CostTracker
             |
             v
Domain Models Layer (ORM Models)
    Users / Roles / Goals / Tasks / Workflows / Leads
    Suppliers / Documents / AIEmployees / AuditLogs
             | SQLAlchemy Async
             v
Database / Storage Layer
    PostgreSQL 16 / SQLite(Dev) / Embedding Vector Store
`

### 2.2 核心数据流转链路（Goal E2E Chain）

`
Boss Natural Language Goal
       |
       v
CEOCommandProcessor.parse_with_llm()  <- LLM Goal Understanding
       | ParsedCommand (KPI/Budget/Time/Risk)
       v
GoalService.create_goal()  -> Persist GoalModel (status=draft)
       | Activate Goal (status=active)
       v
IntelligentPlanner  <- LLM Decompose Steps
       | Plan (Steps + AI Employee Assignment)
       v
AgentRouter  -> Dynamic AI Employee Selection
       |
       v
WorkflowBridge  -> Create WorkflowModel + WorkflowExecutionModel
       |
       v
WorkflowExecutor  -> Create TaskModel(s)
       |
       v
AIEmployee.execute_task
  + Experience Recall -> Real LLM Call (ProviderGateway)
  + Experience Store  -> Record AiCostRecordModel
                       -> Failure -> RecoveryChain Retry
       |
       v
Persist Result -> Update Goal.progress_pct
               -> Update Goal.status (completed/failed)
               -> Dashboard Display
               -> AuditService Full Trail Logging
`

### 2.3 模块依赖方向

`
src/core (zero deps)
    |
    +-> src/database (ORM models) --> src/identity (RBAC/Audit)
    |                                       |
    +-> src/providers (LLM Provider abs)   |
    |        |                              |
    |        v                              |
    +-> src/ai (Agent/Planner/Gateway) <---+
    |        |
    |        v
    +-> src/workflow     --+
    +-> src/tasks          | Called by Service Layer
    +-> src/workforce      |
    +-> src/knowledge      |
    |                      |
    +-> src/business (CRM/Supplier)
            |
            v
    src/api (Routes/Controllers)
            |
            v
    frontend (React SPA)
`



---

## 3. 目录结构

### 3.1 根目录

`
LiuHao-AI-OS/
+-- src/                          # Backend Python source code
|   +-- ai/                       # AI Engine: Agent, Provider, Planner, RAG, Recovery
|   +-- api/                      # FastAPI app: Routes, Dependencies, Factories
|   +-- business/                 # Business layer: Marketing/Sales/Ops/Research/Supplier
|   +-- ceo/                      # CEO Dashboard and models
|   +-- core/                     # Core infra: Config/Encryption/Logging/Events/Modules
|   +-- cost/                     # AI Cost management
|   +-- crm/                      # Acquisition engine: Leads/Quotes/Analysis
|   +-- database/                 # ORM models, repositories, DB connection
|   +-- datasets/                 # Dataset building service
|   +-- evolve/                   # AI Employee evolution, meta-learning, market
|   +-- feedback/                 # User feedback collection & processing
|   +-- governance/               # Approval flows, Risk assessment
|   +-- identity/                 # User, RBAC, Audit, Governance, Visibility
|   +-- integrations/             # External integrations: Email/Templates/Translation/etc
|   +-- jarvis/                   # Voice interaction module (Jarvis)
|   +-- knowledge/                # Knowledge management: Docs/Embedding/RAG/Memory
|   +-- mlops/                    # MLOps: Training/Deployment/A-B testing/Evaluation
|   +-- modules/                  # Plugin modules: CEO Dashboard/Supplier/AI Expert
|   +-- observability/            # Observability: Metrics/Alerts/Tracing
|   +-- providers/                # LLM Provider implementations
|   +-- scheduler/                # Business scheduler: Auto-execute active Goals
|   +-- security/                 # Security: RBAC/ABAC/Policy/Secrets/Tenant isolation
|   +-- site_os/                  # Site network & SEO module
|   +-- sre/                      # SRE: Backup/Scaling
|   +-- tasks/                    # Task management: Models/Service/Executor
|   +-- ui/                       # Backend UI data aggregation services
|   +-- workflow/                 # Workflow engine: Models/Executor/State machine/Templates
|   +-- workforce/                # AI Workforce: Employee/Perf/Cost/Execution queue
|   +-- main.py                   # Entry point (uvicorn src.main:app)
|
+-- frontend/                     # Frontend React application
|   +-- src/
|   |   +-- components/           # Reusable components
|   |   +-- pages/                # Page components (25+ pages)
|   |   +-- routes/               # Routing configuration
|   |   +-- services/             # API clients (by domain)
|   |   +-- i18n.tsx              # Internationalization
|   |   +-- index.css             # Global styles (Tailwind)
|   |   +-- main.tsx              # React entry point
|
+-- tests/                        # Test suite (704 cases, 0 failing @Y1.0)
|   +-- ai/                       # AI layer: Collective intelligence / Trust scoring
|   +-- api/                      # API layer: Dashboard / Workforce / Memory
|   +-- cost/                     # Cost & budget enforcement
|   +-- governance/               # Audit & governance
|   +-- identity/                 # Roles / Permissions / Data scope
|   +-- integration/              # Integration tests (30+ E2E chains)
|   +-- knowledge/                # Knowledge / RAG / Embedding / Semantic search
|   +-- modules/                  # Plugin module tests
|   +-- productization/           # Productization acceptance tests
|   +-- providers/                # Provider switching / Health checks
|   +-- security/                 # RBAC / ABAC security tests
|   +-- sre/                      # SRE production hardening
|   +-- workflow/                 # Workflow execution / Templates
|   +-- conftest.py               # Global pytest fixtures
|
+-- alembic/                      # Database migration scripts
+-- scripts/                      # Startup / Verification scripts (verify_api_smoke.py = post-deploy 28-endpoint smoke; verify_schema_alignment.py; seed_workforce_roster.py)
+-- docs/                         # Acceptance & governance docs
+-- audit_package/                # Audit compliance package
+-- compliance/                   # Compliance checklist
|
+-- docker-compose.yml            # Three-service orchestration
+-- Dockerfile                    # Backend Dockerfile
+-- .dockerignore                 # Exclude .env and sensitive files
+-- .env.example                  # Environment variable template
+-- requirements.txt              # Python dependencies
+-- pytest.ini                    # pytest configuration
+-- alembic.ini                   # Migration configuration
+-- README.md
`

---

## 4. 后端模块详解

### 4.1 src/core - Core Infrastructure (Layer 0)

| File | Responsibility | Key Classes/Functions |
|------|---------------|----------------------|
| core/config.py | Security-first configuration management | Settings, get_settings() |
| core/di.py | Dependency injection container | |
| core/encryption.py | Field-level encryption/masking | |
| core/errors.py | Unified error type hierarchy | LiuHaoError base + 401/403/404/422 subtypes |
| core/events.py | Domain event bus | |
| core/lifecycle.py | Application startup/shutdown lifecycle | get_lifecycle_manager() |
| core/logging.py | structlog structured logging config | |
| core/masking.py | Log sensitive field masking | |
| core/modules/ | Plugin module system | ModuleInterface/ModuleRegistry/EventBus/ModuleLoader |

Configuration security mechanisms:
- SECRET_KEY/JWT_SECRET_KEY forced >=32 chars, otherwise startup error
- Production rejects default values with warning
- CORS origins read from env var; production using * triggers warning

### 4.2 src/providers - LLM Provider Abstraction Layer

| File | Responsibility | Key Classes |
|------|---------------|------------|
| providers/base.py | Unified provider base class | BaseProvider |
| providers/llm_base.py | LLM common abstraction | |
| providers/openai.py | OpenAI-compatible implementations | OpenAIProvider (supports 6 commercial APIs) |
| providers/self_host.py | Self-hosted (Ollama) | OllamaProvider |
| providers/mock.py | Development environment Mock | MockProvider (production blocked) |
| providers/registry.py | Provider registry center | ProviderGateway/ProviderConfig/ModelConfig/ProviderType |

Provider switching rules:
1. LLM_PROVIDER comma-separated (e.g. openai,ollama)
2. Corresponding API Key required, else skipped+warned
3. Ollama needs explicit OLLAMA_ENABLED=true
4. All fail: Dev -> MockProvider fallback (warn); Prod -> sentinel (explicit fail)

### 4.3 src/ai - AI Core Engine Layer

| File | Responsibility | Key Classes/Functions |
|------|---------------|----------------------|
| ai/gateway.py | ProviderGateway singleton entry | get_gateway()/set_gateway()/reset_gateway() |
| ai/agents.py | AI Agent runtime | AgentType(6), AgentConfig, AgentRegistry, AgentRuntime, create_default_agents() |
| ai/planner.py | Intelligent planner: Goal->Step decomposition | IntelligentPlanner |
| ai/goal_service.py | Goal center service (core chain) | GoalService: create_goal()/create_goal_from_text()/activate_goal()/execute_goal() |
| ai/command_processor.py | Boss natural language command parser | CEOCommandProcessor: parse_with_llm() |
| ai/agent_router.py | Dynamic route steps to AI employees | AgentRouter (no employees -> error, no placeholder) |
| ai/workflow_bridge.py | Plan to Workflow persistence | WorkflowBridge |
| ai/orchestrator.py | AI task orchestration | |
| ai/recovery.py | Failure Recovery Chain (do NOT modify) | Failure detection->Decision->Retry/Degrade->Record |
| ai/recovery_executor.py | Recovery chain executor | |
| ai/rag.py | RAG query interface | |
| ai/hybrid_search.py | Hybrid search (vector+keyword) | |
| ai/embeddings.py | Embedding service | |
| ai/chunking.py | Text chunking | |
| ai/cost_tracker.py | LLM invocation cost tracker | Writes AiCostRecordModel |
| ai/memory_store.py | Agent short-term memory | |
| ai/models.py | AI data structures | ParsedCommand etc. |
| ai/reranker.py | RAG reranker | |
| ai/query_expansion.py | Query expansion | |
| ai/tools.py | Agent callable toolset | |

6 Default Agent Types:

| AgentType | Department | Position | Description |
|-----------|-----------|----------|-------------|
| GPT | CEO_OFFICE | CEO_ASSISTANT | CEO Strategic Brain |
| GROK | ANALYTICS | BUSINESS_ANALYST | Intelligence Deputy |
| CLAUDE | ENGINEERING | SYSTEM_ENGINEER | CTO Tech Lead |
| DEEPSEEK | ANALYTICS | DATA_ANALYST | Data Analyst |
| GEMINI | RESEARCH | MARKET_RESEARCHER | Market Researcher |
| KIMI | RESEARCH | PRODUCT_RESEARCHER | Product Researcher (Chinese) |

### 4.4 src/database - Data Access Layer

| File | Responsibility |
|------|---------------|
| database/base.py | SQLAlchemy Base declarative class (shared by all models) |
| database/models.py | 23 core ORM models (see Chapter 6) |
| database/repository.py | Generic repository base class (CRUD abstraction) |
| database/provider_metrics_model.py | Provider metrics persistence |
| database/repositories/ | Domain repositories |

### 4.5 src/identity - Identity and Permissions System

| File | Responsibility | Key Classes |
|------|---------------|------------|
| identity/models.py | User/Role/Permission/Approval data models | User/Role/Permission/RoleEnum/BusinessRole/AccountType/DataScope |
| identity/auth.py | JWT auth / Password hashing | |
| identity/rbac.py | RBAC service | RBACService: Roles/Permissions/Authorization |
| identity/audit.py | Audit log service | AuditService.log() |
| identity/governance.py | Identity governance service | IdentityGovernanceService |
| identity/visibility.py | Data visibility (data permissions) | Owner sees all / Sub-accounts filtered by data_scope |
| identity/database.py | Identity domain DB adapter | |

Account hierarchy (S1):
- OWNER (Main account/Boss): Sees all company data, creates sub-account tasks
- SUB (Sub-account): Data isolation, independent token pool, restricted console
- DataScope: all/department/self three-level data permissions

### 4.6 src/workforce - AI Workforce System (Stage 6)

| File | Responsibility | Key Classes |
|------|---------------|------------|
| workforce/models.py | Workforce domain data structures | AIEmployee, Department(7), Position(17), AIEmployeeStatus |
| workforce/employee.py | Employee lifecycle service | AIEmployeeService: CRUD + Execute task + Experience memory access (Collective Intelligence) |
| workforce/registry.py | Employee persistence repository | AIEmployeeRegistry |
| workforce/performance.py | Performance statistics | Completion rate/Failure rate/Execution time/Cost |
| workforce/cost.py | Employee cost accounting | |
| workforce/execution_queue.py | Task execution queue | |
| workforce/lifecycle.py | Employee state machine | |

AI Employee != Agent != Provider:
- Employee: Business identity (Name/Dept/Position/Permissions/Perf) - Persisted
- Agent: Runtime execution unit (6 AgentTypes), calls Provider
- Provider: Underlying LLM API (7 types)

### 4.7 src/workflow - Workflow Engine

| File | Responsibility | Key Classes |
|------|---------------|------------|
| workflow/service.py | Workflow CRUD + execution service | WorkflowService |
| workflow/executor.py | Workflow executor | Supports inline/background two Worker modes |
| workflow/workflow.py | Workflow engine core | WorkflowEngine/WorkflowStep/WorkflowTask |
| workflow/state_machine.py | Execution state machine | |
| workflow/event_bus.py | Workflow event bus | |
| workflow/templates.py | Workflow template library | |
| workflow/trade_actions.py | Foreign trade business actions | Acquisition/AI Quote/Follow-up closed-loop |
| workflow/trade_templates.py | Foreign trade dedicated workflow templates | |

Execution mode configuration (mitigate long-workflow blocking risk):
- WORKFLOW_WORKER_MODE=inline: Synchronous within request (dev only)
- WORKFLOW_WORKER_MODE=background: Async background execution (prod recommended)
- WORKFLOW_TOTAL_TIMEOUT_SECONDS=1800: 30-min hard timeout
- WORKFLOW_MAX_STEPS=500: Step cap to prevent infinite loops

### 4.8 src/tasks - Task Management

| File | Responsibility | Key Classes |
|------|---------------|------------|
| tasks/models.py | Task domain structures | Task/TaskResult/TaskStatus(6) |
| tasks/service.py | Task service | TaskService: create_task()/create_task_from_assessment() + Audit trail |
| tasks/executor.py | Task executor | Retry logic + Failure Recovery Chain integration |

### 4.9 src/crm - Acquisition Engine (S3)

| File | Responsibility | Key Classes |
|------|---------------|------------|
| crm/models.py | Lead/Activity/Customs models | Lead, LeadActivity, LeadSource, LeadStatus (6 funnel stages) |
| crm/service.py | Lead service | LeadService: Auto acquisition + source_type marking (REAL/MOCK/NOT_CONFIGURED) |
| crm/quotation.py | Smart quotation | QuoteService: AI quote generation |
| crm/analysis.py | Supplier analysis | SupplierAnalysisService |
| crm/engines.py | Acquisition engines | Google/Customs/Social media multi-source mining |

Lead funnel states: NEW -> CONTACTED -> QUALIFIED -> PROPOSAL -> WON / LOST

### 4.10 Supplier Intelligence Sub-module

| File | Responsibility | Key Classes/Functions |
|------|---------------|----------------------|
| business/supplier/models.py | Supplier/Cert/Risk Assessment models | Supplier, SupplierRiskAssessment, RiskLevel(5 levels) |
| business/supplier/risk_agent.py | AI Risk Assessment Agent | SupplierRiskAgent.assess_risk(): Collect->Prompt->AI->Normalize->Persist; Fallback _get_default_assessment() |
| business/supplier/crud.py | Supplier CRUD | |
| business/supplier/validators.py | Data validation | |
| business/supplier/task_adapter.py | Assessment->Task adapter | |
| business/supplier/import_export.py | Batch import/export | |

Supplier Risk Assessment Contract:
- risk_level unified uppercase output: LOW/MEDIUM/HIGH/CRITICAL
- create_task_from_assessment() requires assessment_id (contract)
- actor=None: Task.creator_id = zero-UUID; Audit.user_id=None = system created



### 4.11 src/knowledge - Knowledge Management (Stage 4)

| File | Responsibility | Key Classes |
|------|---------------|------------|
| knowledge/documents.py | Document upload/parse/storage | DocumentService |
| knowledge/embedding.py | Vectorization service | EmbeddingService: Multi-provider support |
| knowledge/chunker.py | Document chunker | |
| knowledge/retrieval.py | Retrieval service | RetrievalService |
| knowledge/knowledge_retrieval.py | Knowledge retrieval augmented | KnowledgeRetrievalService |
| knowledge/rag_pipeline.py | Complete RAG pipeline | |
| knowledge/retriever.py | Vector retriever | |
| knowledge/vector_store.py | Vector store abstraction | |
| knowledge/memory.py | Enterprise long-term memory service | MemoryService + Collective intelligence store/recall (TRUST_THRESHOLD=0.3) |
| knowledge/enterprise_memory.py | Enterprise memory | |
| knowledge/company_brain.py | Company knowledge graph | Entity + Fact two big data models |
| knowledge/security.py | Knowledge base security policy | PII detection + Permission control |
| knowledge/pii.py | Sensitive info recognition | |
| knowledge/processing.py | Document processing pipeline | |

### 4.12 src/integrations - External Integrations

| File | Responsibility | Key Classes |
|------|---------------|------------|
| integrations/email.py | SMTP Email Service | EmailService: Standard lib smtplib (no 3rd-party deps); asyncio.to_thread anti-block; 30s timeout; FAIL records honestly; NEVER forge success |
| integrations/service.py | Multi-platform integration service | PlatformService: Platform status persistent; No creds -> NOT_CONFIGURED |
| integrations/providers.py | Platform provider abstraction | |
| integrations/templates.py | Message template service | TemplateService |
| integrations/translation.py | Translation integration | TranslationService |
| integrations/webhook.py | Platform webhooks | WebhookService |

EmailService Business Contract:
- Sole entry: POST /api/v1/leads/{lead_id}/email (requires lead:update permission)
- Results written to LeadActivity(type=EMAIL); Success stores message_id; Fail stores error_reason
- No credentials configured -> Honestly returns NOT_CONFIGURED; Never forges send-success

### 4.13 src/api - FastAPI Application Layer

| Path | Responsibility |
|------|---------------|
| api/app.py | App entry: lifespan startup + CORS + Error handling + Slow-request monitor + Provider registration + Default employee seeding + Scheduler start |
| api/schemas.py | Request/Response Pydantic Schemas |
| api/dependencies.py | Common Depends |
| api/dependencies/ | database/permissions/approval dedicated Depends |
| api/factories/ | business/knowledge/task/workflow/workforce Service factory functions |
| api/routes/ | 38 route modules (table below) |

API Route Modules (38 modules, mounted at /api/v1):

health, ready, auth, users, roles, permissions, approvals, audit,
dashboard, knowledge, tasks, workflows, workforce, accounts, imports,
platforms, templates, inbox, webhooks, business, supplier, supplier_risk,
ceo, crm, site, market, ai_brain, jarvis, meetings, rag, productization,
provider_status, system, products, quotes, goals, tools, memory

Lifespan startup order (critical path):
1. load_dotenv()                      <- .env MUST load first
2. LifecycleManager.startup()
3. init_database()                    <- Create tables (SQLAlchemy create_all)
4. _initialize_providers()            <- ProviderGateway register 7 Providers
5. _seed_default_employees()          <- 6 AI employees (create if not exist)
6. MarketService.seed_defaults()      <- S5 market default templates/skill packs
7. start_business_scheduler()         <- if SCHEDULER_ENABLED=true

### 4.14 src/modules - Plugin-style Module System

| File | Responsibility |
|------|---------------|
| modules/ceo_dashboard_module.py | CEO Dashboard Module: T5 business anomaly scanning (Lead drop >50% / Churn / High supplier risk) + T10 summary report (KPIs/Alerts/Goal progress/AI costs, independent degradation) |
| modules/supplier_module.py | Supplier plugin module |
| modules/ai_expert_module.py | AI Expert module |

### 4.15 Other Backend Modules

| Module | Responsibility | Key Classes |
|--------|---------------|------------|
| src/cost/ | AI Cost & Budget management | CostManager: Over-spent blocks new LLM calls |
| src/ceo/ | CEO Dashboard models | KPI/Alert/Report data structures |
| src/evolve/ | AI Employee self-evolution | MarketService / MetaLearningService / SelfEvolutionService |
| src/feedback/ | User feedback handling | FeedbackService: Feedback -> Improvement closed-loop |
| src/governance/ | Enterprise governance | ApprovalService (approval flows) / Risk assessment |
| src/jarvis/ | Voice assistant | JarvisService + Wake word / ASR / TTS / Multi-lang detection |
| src/mlops/ | Model operations | Training / Deployment / A-B test / Model registry / Evaluation |
| src/observability/ | Observability | Metrics / Alerts / Tracing (Prometheus compatible) |
| src/scheduler/ | Business scheduler | Periodically execute active Goals (boss long absence autonomous ops) |
| src/security/ | Second security implementation | RBAC/ABAC/Policy engine/Secrets management/Tenant isolation |
| src/site_os/ | Site network SEO | SiteService: Sitemap/robots.txt/SEO file generation |
| src/sre/ | SRE operations | Auto backup / Elastic scaling |
| src/datasets/ | Datasets | DatasetService: Training data construction |
| src/ui/ | Backend UI aggregation | Frontend page data aggregation services |

---

## 5. Frontend Module Details

### 5.1 Technical Configuration

`
Framework:  React 18.3 + TypeScript 5.5
Build:      Vite 5.4 (dev port 3000)
Styling:    TailwindCSS 3.4 + PostCSS + Autoprefixer
Routing:    React Router v6 (BrowserRouter)
HTTP:       Native fetch (services/api.ts wrapper)
Icons:      Lucide React
Testing:    Vitest 1.6 + @testing-library/react 14
Storybook:  8.6.18 (port 6006)
Proxy Prod: Nginx (frontend/nginx.conf), port 80 -> /api proxies to backend 8000
`

### 5.2 Page System (27 Pages)

Main Account Full Console:
/dashboard         DashboardPage          Boss Dashboard: KPIs/Alerts/AI Costs/Activity feed
/goals             GoalCenterPage         Goal Center: Create/Activate/Track Goal
/employees         EmployeeManagementPage AI Employee Mgmt (new, with Trust/Capability/Risk scores)
/workflow          WorkflowPage           Workflow definition/Execution monitoring
/leads             LeadsPage              Lead pool / Sales funnel (NEW->WON)
/quotes            QuotesPage             Quote management
/supplier-analysis SupplierAnalysisPage   Supplier Intelligence + Risk Assessment
/weekly-report     ReportPage             Weekly report / Business summary
/weekly-meeting    WeeklyMeetingPage      Weekly meeting AI minutes
/platforms         PlatformPage           Multi-platform connection status
/platforms/inbox   InboxPage              Unified message inbox
/platforms/templates MessageTemplatesPage Message templates
/imports           ImportPage             Batch data import
/accounts          AccountsPage           Account management
/sub-accounts      SubAccountManagementPage Sub-account mgmt (incl. monthly budget)
/approvals         ApprovalQueuePage      Approval queue
/permissions       PermissionCenterPage   Permission center (RBAC)
/security          SecurityPage           Security config
/models            ModelsPage             AI models / Provider management
/metrics           MetricsPage            Prometheus metrics
/market            MarketPage             AI employee skill marketplace
/company           CompanyPage            Company profile
/site              SitePage               Site network management
/seo               SEOPage                SEO configuration
/onboarding        OnboardingPage         First-time guide
/login             LoginPage              Login

Sub-Account Dedicated Restricted Console:
/sub-portal        SubPortalPage (Sub home)
+ accessible: leads / weekly-report / weekly-meeting / platforms / inbox / templates / supplier-analysis / site / seo

### 5.3 Common Components

Layout / SubLayout / Header / Sidebar
AIWorkStatus - Real-state status badges (Never uses pure animation to fake AI work):
  Employee: Working/Idle/Waiting/Failed
  Goal:     Planning/Executing/Recovering/Completed/Failed
  Workflow: Running/Waiting/Recovery/Completed
  Platform: Connected/Syncing/Error/NotConfigured
AIActivityFeed - AI activity stream (real Audit record display)
AIEmptyState - Empty state placeholder

### 5.4 Route Auth Logic (AppRoutes)

`
Load:
  + No token -> redirect /login
  + Token -> Promise.race([fetchMe(), 8s timeout])
  |    + Success: account_type=owner -> Layout + Full Console
  |    |                  =sub   -> SubLayout + Restricted Console
  |    + Fail(network/expired): clearAuthToken() -> /login
  + Timeout(8s): Same fail logic
`



---

## 6. Database Models

### 6.1 Core ORM Models Overview (23+)

Grouped by domain:

#### Identity & Tenant Domain

enterprises       EnterpriseModel       id(UUID), name
tenants           TenantModel           tenant_id, enterprise_id, owner_id, status
users             User                  username, email, hashed_password, role
                                      account_type (owner/sub), business_role (5 types)
                                      data_scope (all/department/self)
roles             Role                  name (admin/user/viewer)
permissions       Permission            resource:action strings
role_permissions  (Association table)   role_id + permission_id M2M

#### Knowledge Domain (S4)

documents              DocumentModel            filename, content, summary, embedding, content_hash, status
document_chunks        DocumentChunkModel       document_id(FK), chunk_text, chunk_index, metadata_
embedding_storage      EmbeddingStorageModel    document_id, chunk_id, vector(JSON), dimension, provider, embedding_model
memories               MemoryModel              agent_id, user_id, content, memory_type (3 types), importance, context, session_id, access_count
company_brain_entities CompanyBrainEntityModel  name, entity_type, attributes, relationships, company_id
company_brain_facts    CompanyBrainFactModel    entity_id, attribute, value, source, confidence (6 levels), priority, is_active, supersedes

#### Workflow & Task Domain (S5)

workflows             WorkflowModel             name, version, steps(JSON), enabled, created_by
workflow_executions   WorkflowExecutionModel    workflow_id(FK), user_id, status (uppercase 5 states), variables, result, error, timestamps
tasks                 TaskModel                 title, task_type, status (6), priority, assigned_to, creator_id, workflow_id, parent_task_id, retry_count, max_retries, input/result_data
task_results          TaskResultModel           task_id, success, output, error, execution_time_seconds
business_tasks        BusinessTaskModel         Business-layer task extension

#### AI Workforce & Cost Domain (S6)

ai_employees          AIEmployeeModel           name, department, position, agent_type, provider_config(JSON), status
                                                    trust_score, capability_score, risk_score
                                                    tasks_completed, tasks_failed, total_cost_usd, owner_id
agent_memories        AgentMemoryModel          agent_id, memory_type, content, context(JSON)
ai_cost_records       AiCostRecordModel         provider, model, input/output_tokens, cost_usd, latency_ms, status, timestamp
employee_performance  EmployeePerformanceModel  employee_id, period, tasks_completed, success_rate, avg_latency, total_cost
employee_costs        EmployeeCostModel         employee_id, period, cost_usd, token_usage

#### Goal & Failure Recovery Domain (P0)

goals                 GoalModel       title, description, priority, status (draft/active/completed/failed)
                                            kpi_name, kpi_target, kpi_unit
                                            budget_total, budget_spent, progress_pct
                                            time_start, time_end, created_by, tenant_id
                                            plan(JSON)
failure_records       FailureRecordModel  component, error_message
                            recovery_status (pending/recovered/failed), retry_count
                            resolution, goal_id, task_id, workflow_execution_id

#### Business Domain

leads               Lead        source (5 types), source_type (REAL/MOCK/NOT_CONFIGURED),
                                name, company, country, email, whatsapp, status (funnel 6 stages),
                                priority, score, estimated_value, quote_amount, won_amount
lead_activities     LeadActivity  lead_id, type (CALL/EMAIL/MESSAGE/MEETING/NOTE),
                                  content, status (sent/failed/NOT_CONFIGURED), message_id, error_reason
suppliers           Supplier    name, code, country, business_type, status, credit_rating,
                                risk_level (5 levels), source_type
supplier_risk_assessments  SupplierRiskAssessment  supplier_id, risk_level (5 uppercase),
                                factors(JSON), recommendations(JSON), score (0-100),
                                provider, ai_model, source_type (REAL/RULE_BASED/MOCK)

#### Scheduling & Platform Domain

meetings   MeetingModel    title, date, content(JSON), created_by
messages   MessageModel    platform, channel, sender, recipient, content, source_type
products   ProductModel    sku, name, category, price, cost, specs(JSON)

---

## 7. Key Classes & Functions

### 7.1 Goal E2E Chain Core (P0 Boss Goals)

GoalService (src/ai/goal_service.py)

create_goal_from_text(text, user=None) -> (GoalModel, parse_info)
  # Natural language -> Goal (honest degradation: LLM -> Rule)
  # parse_info.parse_method = LLM / RULE_FALLBACK / MOCK

activate_goal(goal_id, user=None) -> GoalModel
  # 1. IntelligentPlanner decomposes Steps (no LLM degrades to template, never empty)
  # 2. AgentRouter dynamically selects existing AI Employees (none -> ValueError, no placeholder)
  # 3. Plan persisted to GoalModel.plan(JSON)
  # 4. Goal.status -> active

execute_goal(goal_id, user=None) -> GoalModel
  # WorkflowBridge -> WorkflowService -> WorkflowExecutor
  # -> Create TaskModel(s)
  # -> AIEmployeeService.execute_task (Real LLM, AiCostRecord persisted)
  # -> Failure goes through Failure Recovery Chain Retry
  # -> Success: Goal.progress_pct update -> completed
  # -> Full AuditService.log(...)

### 7.2 Supplier Risk Assessment Closed-loop

SupplierRiskAgent.assess_risk(supplier_id) -> dict (src/business/supplier/risk_agent.py)
  # Contract (required output fields):
  {
    assessment_id: str,        # create_task_from_assessment contract requirement
    risk_level: LOW|MEDIUM|HIGH|CRITICAL,  # UPPERCASE
    score: 0..100,
    factors: [...],
    recommendations: [...],
    source_type: REAL|RULE_BASED|MOCK,
    provider: str,
    ai_model: str,
  }
  # Pipeline: Collect data -> Prompt -> ProviderGateway.chat -> Normalize -> Persist
  # Exceptions fall back to _get_default_assessment() (graceful degrade)

TaskService.create_task_from_assessment(assessment, actor_id=None) (src/tasks/service.py)
  # Contract:
  # 1. assessment MUST contain assessment_id (else ValueError)
  # 2. actor=None -> Task.creator_id = 00000000-0000-0000-0000-000000000000
  #               Audit.user_id = None (= system-created)
  # 3. Task.metadata[assessment_reference] = assessment_id
  # 4. AuditService.log(action=TASK_CREATED_FROM_ASSESSMENT, ...)

### 7.3 Provider Gateway (7 LLM Unified Entry)

ProviderGateway (src/providers/registry.py)
  register_provider(config: ProviderConfig)
  register_model(config: ModelConfig)
  list_providers() -> list[ProviderConfig]
  list_models(provider=None) -> list[ModelConfig]
  async chat(provider, model_id, messages, **kwargs) -> ProviderResponse
    # Unified chat interface
    # ProviderResponse fields: content, usage{prompt_tokens,completion_tokens,total_tokens},
    #                         latency_ms, raw_response
    # AiCostRecord synchronously recorded on caller side

ModelConfig
  provider: ProviderType (OPENAI/ANTHROPIC/GOOGLE/DEEPSEEK/XAI/MOONSHOT/OLLAMA)
  model_id: str (gpt-4o-mini / qwen2.5:3b etc.)
  context_window: int (32768 / 128000 / 1M)
  input_cost_per_1k: float (USD)
  output_cost_per_1k: float

### 7.4 AI Employee Service (Collective Intelligence)

AIEmployeeService.execute_task(employee_id, task, actor=None)
  # Execution pipeline (critical):
  # 1. Recall experience recall_agent_experience(employee) -> inject prompt context
  # 2. ProviderGateway.chat() -> Real LLM call (record AiCostRecord)
  # 3. Persist TaskModel.result_data / updated_at
  # 4. Write experience store_agent_experience(employee, task, result)
  # 5. Update employee.tasks_completed / total_cost_usd

Collective Intelligence (src/knowledge/memory.py)
  TRUST_THRESHOLD = 0.3
  store_agent_experience(employee, task, result, success)
    # -> MemoryModel: user_id=employee.id, memory_type=procedural
    # context = {task_type, input, result, success, trust_score=employee.trust_score}

  recall_agent_experience(employee, task_type) -> list
    # Recalls employee + colleague experience (only records with trust_score >= threshold)
    # Trust mechanism prevents low-quality experience from polluting collective memory

### 7.5 EmailService (Standard Library Implementation, No 3rd-party Deps)

EmailService (src/integrations/email.py)
  SMTP Email Service - Honest Email Delivery
  - Config from env vars (SMTP_HOST/PORT/USER/PASSWORD/FROM/USE_SSL/PROXY)
  - Not configured -> status=NOT_CONFIGURED, NEVER forges success
  - asyncio.to_thread(smtplib.sendmail) prevents event loop blocking
  - 30s socket timeout
  - Sole business entry: POST /api/v1/leads/{lead_id}/email (need lead:update)
  - Results persisted to LeadActivity(type=EMAIL)
      Success -> LeadActivity.status=sent, message_id=<SMTP message-id>
      Fail    -> LeadActivity.status=failed, error_reason=str(e)

  async send_lead_followup(lead_id, subject, body, actor_user=None) -> dict
    if not _configured(): return {status: NOT_CONFIGURED, ...}
    try:
      msg_id = await asyncio.to_thread(functools.partial(_send_sync, msg, timeout=30))
      return {status: sent, message_id: msg_id, ...}
    except Exception as e:
      return {status: failed, error: str(e), ...}

### 7.6 FastAPI Application Entry

create_app() -> FastAPI (src/api/app.py)
  Returns configured FastAPI instance (Dockerfile CMD calls)
  1. lifespan: Initialize DB/Provider/Employees/Scheduler
  2. CORS: settings.cors_origins comma-separated list
  3. Slow-request monitoring middleware: >500ms warning + X-Response-Time-Ms header
  4. Unified exception handler: LiuHaoError -> Maps to HTTP 401/403/404/422
  5. include_router(api_router, prefix=/api/v1)
  6. Root GET / -> Returns name/version/status

---

## 8. Dependencies

### 8.1 Python Backend Dependencies (requirements.txt)

fastapi>=0.111.0                 Backend web framework
uvicorn[standard]>=0.30.0         ASGI server
sqlalchemy>=2.0                  ORM (async support)
aiosqlite>=0.20                  SQLite async driver (dev)
asyncpg>=0.29                    PostgreSQL async driver (prod)
pydantic[email]>=2.0             Data validation + Settings
pydantic-settings>=2.0            Env var loading
python-dotenv>=1.0                .env file loading
python-multipart>=0.0.9           File upload parsing
structlog>=24.0                   Structured JSON logging
pytest>=8.0 / pytest-asyncio>=0.23 / pytest-cov>=5.0   Testing framework
httpx>=0.27                       Async HTTP client (Provider calls/tests)
ollama>=0.4                       Official Ollama client
passlib[bcrypt]>=1.7              Password hashing (bcrypt)
python-jose[cryptography]>=3.0    JWT signing/verification (HS256)
jinja2>=3.0                       Template engine
pandas>=2.0 / openpyxl>=3.1       Data import (Excel/CSV)

### 8.2 Frontend Dependencies (package.json)

react 18.3.1 / react-dom 18.3.1    UI framework
react-router-dom 6.26.0             Routing
typescript 5.5.4                    Type system
vite 5.4.2                          Build tool
tailwindcss 3.4.10                  Atomic CSS
lucide-react 0.441.0                Icon library (300+)
@testing-library/react 14.2.1       Frontend component testing
vitest 1.6.0                        Frontend test runner
storybook 8.6.18                    Component documentation library
jsdom 24.0.0                        Vitest DOM environment

### 8.3 Key Module Call Chain (No Circular Deps)

Goal E2E:
  routes/goals.py
    -> GoalService (src/ai/goal_service.py)
        -> CEOCommandProcessor (src/ai/command_processor.py) -> ProviderGateway
        -> IntelligentPlanner (src/ai/planner.py) -> ProviderGateway
        -> AgentRouter -> AIEmployeeRegistry + RBACService
        -> WorkflowBridge -> WorkflowService
            -> WorkflowExecutor -> TaskService
                -> TaskExecutor -> AIEmployeeService.execute_task
                    -> AgentRuntime -> ProviderGateway
                                  -> cost_tracker -> AiCostRecordModel
                                  -> Failure Recovery Chain
                    -> store_agent_experience (src/knowledge/memory.py)
                    -> AuditService

Supplier Risk Pipeline:
  routes/supplier_risk.py
    -> SupplierRiskAgent.assess_risk -> ProviderGateway
    -> TaskService.create_task_from_assessment
        -> TaskModel persistence + AuditService.log



---

## 9. Core Business Flows

### 9.1 Supplier Risk Assessment -> Task -> Audit (Step 2 Core Closed-loop)

1. Boss/Operator clicks Risk Assessment on SupplierAnalysisPage
   POST /api/v1/supplier/risk/assess/{supplier_id}
2. SupplierRiskAgent.assess_risk(supplier_id)
   + Collect supplier data (basic info + certs + history)
   + Prompt -> ProviderGateway.chat (Real LLM or Mock)
   + Parse JSON: Failures use _get_default_assessment fallback
   + Normalize: risk_level -> UPPERCASE (LOW/MEDIUM/HIGH/CRITICAL)
   + Persist SupplierRiskAssessment + Write knowledge base
   Return JSON containing assessment_id
3. (Optional) Auto/manual trigger TaskService.create_task_from_assessment(assessment)
   + Validate assessment_id required
   + Create Task: type=supplier_risk_mitigation, High-risk auto sets priority=HIGH
   + Task.metadata[assessment_reference] = assessment_id
   + AuditService.log(action=TASK_CREATED_FROM_ASSESSMENT, actor=system/user, ref=assessment_id)
4. Dashboard task list shows this task, assignable to AI Employee
5. AI Employee executes -> Result persisted -> Audit log -> Task closed

### 9.2 Foreign Trade Business Automation Closed-loop (Acquisition -> Quote -> Follow-up)

1. MarketingService / CRM LeadService
   + Multi-source lead mining (Google Custom Search / Customs / Social)
   |   Configured real creds -> source_type=REAL; Otherwise -> source_type=MOCK
   + Lead scoring + persistence
2. Workflow Foreign Trade Auto Acquisition Follow-up (trade_templates.py)
   Step1: Lead info validation
   Step2: QuoteService.AI Quote (consider product spec/shipping/duties)
   Step3: EmailService.send_lead_followup()
     Configured SMTP -> source_type=REAL -> Real delivery
       Success -> LeadActivity(type=EMAIL, status=sent, message_id=<...>)
       Fail    -> LeadActivity(type=EMAIL, status=failed, error_reason=...)
     NO SMTP config -> NOT_CONFIGURED (Never forge success)
   Step4: PlatformService platform messages (WhatsApp/Facebook)
     No configured platform -> source_type=NOT_CONFIGURED
3. Lead.status updates -> QUALIFIED -> PROPOSAL -> WON / LOST
4. Dashboard updates funnel KPIs / Won Amount / ROI
   No real revenue -> ROI_UNAVAILABLE (Never forge ROI)

### 9.3 Failure Recovery Chain (Already Accepted - Do NOT Destroy)

Task/Workflow execution failure:
   Catch Exception
1. Persist FailureRecordModel (component/error/recovery_status=pending)
2. RecoveryChain Decision:
   retry_count < max_retries & Retriable error -> Exponential backoff retry
   Non-retriable error -> Degrade (switch Provider / Use rules / Partial result)
   Retries exhausted + Degrade failed -> recovery_status=failed
3. Each retry -> FailureRecordModel.retry_count += 1
4. Recovery success -> recovery_status=recovered, record resolution
5. Full persistence: Goal.status -> failed ONLY when Recovery Chain completely fails
   Goal.progress_pct = successfully completed steps %

### 9.4 Dynamic Trust Scoring System (AI Workforce Risk Management)

After each AI Employee task execution:
  success_rate   = tasks_completed / (tasks_completed + tasks_failed)
  recovery_rate  = recovered_failures / total_failures
  permission_scope = count(assigned high-risk permissions)
  historical_behavior = recent_violations_weighted

  trust_score      = f(success_rate, recovery_rate, task_history_age)   [0.0 - 1.0]
  capability_score = f(avg_quality, task_complexity_completed)          [0.0 - 1.0]
  risk_score       = f(permission_scope, historical_behavior, failure_recentness)  [0.0 - 1.0]

High-risk permission granting rules (Fail Closed):
  - trust_score < 0.5  -> Auto DENY
  - 0.5 <= trust_score < 0.7 -> Requires approval flow (ApprovalQueue)
  - trust_score >= 0.7 -> Auto grant (continuous monitoring)

Collective intelligence experience sharing threshold:
  recall_agent_experience returns colleague experience where
    employee.trust_score >= TRUST_THRESHOLD (0.3)

---

## 10. Running & Deployment

### 10.1 Local Development Environment

Environment requirements:
- Python 3.10 OR 3.11
- Node.js 18+ / npm
- (Optional) Ollama local LLM service

Steps:

`ash
# 1. Clone & enter
cd LiuHao-AI-OS

# 2. Backend venv
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt

# 3. Frontend deps
cd frontend
npm install
cd ..

# 4. Env config
copy .env.example .env            # Windows
# cp .env.example .env            # Linux/Mac
# Edit .env: SECRET_KEY, JWT_SECRET_KEY (each >=32 chars)
# Optional: OPENAI_API_KEY / OLLAMA_ENABLED / SMTP_* etc.

# 5. Start backend (port 8000)
bash scripts/start_api.sh         # OR uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start frontend (port 3000)
bash scripts/start_frontend.sh    # OR cd frontend && npm run dev
`

Access URLs:
- Frontend console:  http://localhost:3000
- Backend API:       http://localhost:8000
- Swagger docs:      http://localhost:8000/docs
- Health check:      http://localhost:8000/api/v1/health/ready
- Provider status:   http://localhost:8000/api/v1/provider/status

### 10.2 Run Tests Locally

`ash
set SECRET_KEY=test12345678901234567890123456789012
set JWT_SECRET_KEY=test12345678901234567890123456789012

# Full regression (~650 cases)
pytest -q

# Isolated key chains
pytest tests/integration/test_e2e_chain.py -v                    # Goal E2E
pytest tests/integration/test_failure_recovery_chain.py -v        # Recovery Chain
pytest tests/integration/test_supplier_risk_task_pipeline.py -v   # Supplier closed-loop
pytest tests/integration/test_email_smtp.py -v                    # EmailService

# Frontend tests
cd frontend
npm run test           # Vitest
npm run build          # Prod build (includes tsc --noEmit type check)
`

### 10.3 Docker Production Deployment

Pre-deployment checklist:
1. Overseas server (recommend Ubuntu 22.04): Ensure outbound SMTP / LLM API access
2. Server .env file (NEVER commit to Git / NEVER write in docker-compose.yml):
   SECRET_KEY=32+ char true random string
   JWT_SECRET_KEY=32+ char true random string
   POSTGRES_PASSWORD=strong password
   LLM_PROVIDER=openai          # OR ollama,deepseek etc.
   OPENAI_API_KEY=sk-xxx        # Corresponding Provider Key
   SMTP_HOST=smtp.gmail.com     # Optional
   SMTP_USER=you@company.com
   SMTP_PASSWORD=16-char-app-password
   SMTP_FROM=you@company.com
   SCHEDULER_ENABLED=true       # Autonomous ops (optional)
3. Docker Engine + Docker Compose v2 installed

Deployment Commands:

`ash
# 1. Validate compose syntax + env injection (MUST PASS)
docker compose config > /dev/null && echo CONFIG OK

# 2. Verify Docker build context does NOT include .env (MUST)
docker build -t liuhao-check --no-cache --progress=plain . 2>&1 | grep -i copy.*.env || echo SAFE

# 3. Build & start 3 services in background
docker compose up -d --build

# 4. Health check (3 containers all healthy)
docker compose ps
# Expected:
#   liuhao-database  healthy
#   liuhao-backend   healthy  (Runs /api/v1/health/ready)
#   liuhao-frontend  running (No built-in health check)

# 5. Check backend logs: Provider is REAL?
docker logs liuhao-backend | grep -E provider_registered|using_mock_provider|production_blocked

# 6. Browser visit
# http://<server-ip>   (Nginx listens 80 -> frontend, /api proxies to backend 8000)
`

Container Network:
`
Browser -> 80 (frontend container Nginx)
              + /     -> Frontend static assets (Vite build)
              + /api  -> Proxy to backend:8000
                              |
                              + 5432 (database container PostgreSQL 16)
backend -> host.docker.internal:11434 (Host Ollama, optional)
backend -> External SMTP / LLM APIs
`

Post-deploy end-to-end verification:
`ash
# 1. Readiness endpoint (ready, no degraded items)
curl http://localhost/api/v1/health/ready

# 2. Provider status (not using_mock)
curl http://localhost/api/v1/provider/status
`

---

## 11. Test System

### 11.1 Test Layered Structure (~650+ cases)

tests/integration/    ~30 test files    Integration/E2E  Cross-module, business closed-loop
tests/productization/ 13 files          Product acceptance  Frontend-backend connectivity, persistence
tests/knowledge/      11 files          Module tests       Docs/Embeddings/RAG/Semantic search
tests/ai/             2 files           AI capabilities    Collective intelligence / Trust scoring
tests/modules/        2 files           Plugin modules     CEO business alerts / Summary report
tests/security/       2 files           Security tests     RBAC + ABAC unified, permission enforcement
tests/governance/     2 files           Governance         Audit, 8 governance capabilities
tests/identity/       2 files           Identity system    Business roles / Data visibility isolation
tests/workflow/       3 files           Workflow           Phase3 execution / Trade templates / Safety
tests/cost/           2 files           Cost control       Budget over-spend blocking / Cost records
tests/providers/      3 files           Providers          Switching / Health checks / Self-host
tests/sre/            2 files           SRE                Prod secret hardening / Backup scaling
tests/tenant/         1 file             Multi-tenant       Tenant-level data isolation
tests/site_os/        2 files           Site network       SEO file generation / source_type honesty
tests/scheduler/      1 file             Scheduler          Autonomous ops periodic execution
tests/observability/  1 file             Observability      Metric collection alerts
tests/feedback/       1 file             Feedback           Feedback processing pipeline
tests/mlops/          3 files           MLOps              Train/Deploy/AB-test pipeline
tests/api/            5 files           API layer          Dashboard / Memory / Trust / Workforce
tests/frontend/       1 file             Frontend product   Phase7 frontend console acceptance
tests/load/           1 file             Performance        Baseline load benchmark
tests/s6/             1 file             S6 smoke           S6 production readiness smoke test

### 11.2 Must-pass Acceptance Tests

`ash
# Core chains (zero failure allowed)
pytest tests/integration/test_e2e_chain.py::test_goal_from_text_to_completed -v
pytest tests/integration/test_failure_recovery_chain.py -v
pytest tests/integration/test_supplier_risk_task_pipeline.py -v

# Production security hardening (absolutely NO failure)
pytest tests/sre/test_production_secrets_hardening.py -v
pytest tests/security/test_rbac_abac.py -v

# Provider honesty (NO faking success allowed)
pytest tests/integration/test_crm_execution_mode.py -v
pytest tests/integration/test_platform_execution_mode.py -v

# Full regression (target 650+ passed, 0 failed)
pytest -q
`

pytest.ini configuration:
  asyncio_mode = auto
  testpaths = tests
  markers: slow, integration, unit, e2e

---

## 12. Security & Governance

### 12.1 Security Layering

Layer 1 - Transport security:  Nginx reverse proxy (TLS recommended in prod) + JWT
Layer 2 - Authentication:      JWT HS256 + bcrypt password hash; Default-secret rejected in prod
Layer 3 - Authorization RBAC:  Role->Permission M2M; Fail Closed default deny
Layer 4 - Authorization ABAC:  Attribute-based fine-grained (subject/object/environment)
Layer 5 - Data visibility:     DataScope.ALL/DEPARTMENT/SELF; Owner full, Sub restricted
Layer 6 - Multi-tenant iso:    tenant_id filtering; Tests verify cross-tenant invisible
Layer 7 - Approval flows:      High-risk ops PENDING->APPROVED before execution
Layer 8 - Audit logs:          All critical ops AuditService.log persisted; Full traceability
Layer 9 - Secrets management:  Injected via env vars; .dockerignore excludes .env; .env not in image
Layer 10 - CORS:               settings.cors_origins comma-list; Prod * triggers warning
Layer 11 - Autonomous op sec:  Execution scope / Risk limits / High-risk interception / Log viewing / Auto-stop
Layer 12 - Provider prod sec:  Prod no real Provider -> sentinel, calls explicitly fail (NEVER silent Mock)

### 12.2 Audit Compliance (audit_package/)

audit_package/
  security_policy.md              Security Policy
  data_policy.md                  Data Lifecycle Policy
  risk_handling_procedure.md      Risk Handling Procedure
  operations_procedure.md         Operations Procedure
  system_architecture.md          System Architecture Description

### 12.3 Data Source Honesty Requirements (Fail Closed for Faking)

Scenario                       | Behavior without real credentials/data  | Forbidden
Lead acquisition engine        | source_type=MOCK, returns sample data    | Forging REAL to create real Leads
Platform message sending       | source_type=NOT_CONFIGURED, explicit err | Forging success status / message_id
SMTP email sending             | NOT_CONFIGURED, return unconfigured      | Forging sent status / message_id
AI supplier/customer analysis  | NOT_CONFIGURED / RULE_BASED w/ degrade   | Marking REAL, disguising templates as AI analysis
Market event creation          | Explicit return no real data source, nc  | Forging real market events
Health check / Provider status | using_mock=true / production_blocked     | UI displaying Connected (should Not Configured)
AI working status              | Waiting / Not Configured (real backend)  | Pure animations faking AI working
ROI calculation                | ROI_UNAVAILABLE, revenue missing stated  | completed * 100.0 / fake numbers
LLM cost recording             | All real calls record 6 cost fields      | Calling w/o recording cost

---

## 13. Configuration Reference

### 13.1 Complete Environment Variable List (.env.example)

Application Basics
  APP_ENV              development        development / staging / production
  APP_HOST             0.0.0.0            Bind address
  APP_PORT             8000               Backend port
  SECRET_KEY           **REQUIRED**       >=32 chars, session/general signing key
  JWT_SECRET_KEY       **REQUIRED**       >=32 chars, JWT signing key
  CORS_ORIGINS         *                  Comma-separated allowed origins (prod restrict domains)
  LOG_LEVEL            INFO               DEBUG / INFO / WARNING / ERROR

Database
  DATABASE_URL         sqlite+aiosqlite:///./dev.db    Direct URL (preferred)
  POSTGRES_HOST        localhost                        PG host when DATABASE_URL unset
  POSTGRES_PORT        5432                             PG port
  POSTGRES_DB          liuhao_ai_os                     PG database
  POSTGRES_USER        liuhao_user                      PG user
  POSTGRES_PASSWORD    (required for PG)                PG password

OpenAI
  OPENAI_API_KEY       (optional)         sk-xxx; When configured -> source_type=REAL
  OPENAI_BASE_URL      https://api.openai.com/v1
  OPENAI_CHAT_MODEL    gpt-4o-mini
  OPENAI_EMBED_MODEL   text-embedding-3-small

Ollama (self-hosted)
  OLLAMA_ENABLED       false              **MUST explicitly true to enable**
  OLLAMA_HOST          http://localhost:11434    Docker need host.docker.internal:11434
  OLLAMA_DEFAULT_MODEL qwen2.5:3b        Recommend 3B for non-GPU envs
  OLLAMA_KEEP_ALIVE    (optional)         Minutes; needs Ollama service restart after change
  OLLAMA_NUM_THREADS   (optional)         Thread count; same above

Acquisition data sources (optional)
  GOOGLE_SEARCH_API_KEY    (optional)     Google source -> REAL when configured
  GOOGLE_SEARCH_CX         (optional)     Search Engine ID
  CUSTOMS_API_URL          (optional)     Customs data source URL

SMTP Email (optional)
  SMTP_HOST            (optional)         Unconfigured -> Email NOT_CONFIGURED
  SMTP_PORT            587                587 STARTTLS / 465 SSL
  SMTP_USER            (optional)         Sender account
  SMTP_PASSWORD        (optional)         App-specific password (NOT login pwd)
  SMTP_FROM            (optional)         Default = SMTP_USER
  SMTP_USE_SSL         false              Port 465 change to true
  SMTP_PROXY           (optional)         socks5://host.docker.internal:10808 when blocked

Network proxy (optional)
  HTTP_PROXY / HTTPS_PROXY / ALL_PROXY    (optional) httpx/Provider outbound proxy
  NO_PROXY             localhost,127.0.0.1,host.docker.internal,database,postgres,backend,frontend

Business Scheduler (Autonomous ops)
  SCHEDULER_ENABLED             false     true -> Periodically execute active Goals
  SCHEDULER_INTERVAL_SECONDS    300       Minimum 30 seconds
  SCHEDULER_AUTO_ACTIVATE       false     Auto activate drafts (full autonomy, cautious)
  SCHEDULER_MAX_GOALS_PER_CYCLE 5

Workflow execution
  WORKFLOW_WORKER_MODE               inline    inline(sync) / background(async, prod recommended)
  WORKFLOW_TOTAL_TIMEOUT_SECONDS     1800      30 min hard timeout
  WORKFLOW_MAX_STEPS                 500       Prevent infinite loops

Other
  PYTHONPATH           .            Keep, relative imports require it

---

## Appendix A: Common Troubleshooting

Symptom                                    | Probable Cause                         | Solution
Startup err SECRET_KEY <32 chars           | .env unset or length<32                | Generate >=32 char random, write to .env
Frontend 401 redirect infinite loop        | Backend 8000 unreachable / JWT CORS    | Check backend health; CORS_ORIGINS includes frontend domain
Goal activation No available AI employee   | Seeding not ran / all RETIRED          | Restart backend; check /api/v1/workforce/employees
Docker backend still mock provider         | .env LLM_PROVIDER/Key not in container | docker compose config; verify host .env location
Ollama Docker cant reach host              | OLLAMA_HOST=localhost wrong           | .env set OLLAMA_HOST_DOCKER=http://host.docker.internal:11434
SMTP Connection timed out (China net)      | Ports 587/465 blocked                 | Set SMTP_PROXY=socks5://host.docker.internal:10808; Or deploy overseas
pytest all fail DB constraint errors       | Tests sharing SQLite instance          | Ensure DATABASE_URL not file-based; conftest.py handles isolation
Long workflow HTTP timeout                 | Worker mode inline, blocks HTTP        | Set WORKFLOW_WORKER_MODE=background

---

*End of Document - LiuHao AI OS Y1.0 Code Wiki*

