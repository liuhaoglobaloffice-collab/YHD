# Y1 Requirement Traceability

来源：MASTER_BLUEPRINT_Y1.md, MASTER_BLUEPRINT_Y1_FINAL.md

说明：本文件为 Y1 需求追踪与验证主表。每项记录：Requirement、实现位置、证据路径、当前状态、测试、已识别缺口、优先级。

| Requirement ID | Blueprint Source | Requirement | Current Implementation | Evidence | Status | Test | Gap | Priority |
|---|---|---|---|---|---:|---|---|---:|
| REQ-001 | BOTH | Identity: 独立、稳定、加密凭证、恢复元数据 | core/identity (Identity, store, HTTP API) | core/identity/* | Implemented | core/identity/test_*.py, core/identity/test_api.py | Key management (master key persistence/KMS) | High |
| REQ-002 | BOTH | Core: 管理 Identity/Context/Planning/Orchestration | core/core (Session, HTTP API) | core/core/* | Implemented | core/core/test_*.py, core/core/test_api.py | Scale/permissions/RBAC | High |
| REQ-003 | BOTH | Model Gateway: 统一认证、路由、归一化、计费、审计 | core/model_gateway (routing + audit + traces) | core/model_gateway/* | Implemented | core/model_gateway/test_*.py | Billing/normalization/quotas | High |
| REQ-004 | BOTH | Model Manager: 生命周期（发现/下载/验证/部署/回滚） | core/model_manager (lifecycle) | core/model_manager/* | Implemented | core/model_manager/test_*.py | Registry UI, persistence hardening | High |
| REQ-005 | BOTH | Provider Adapter: 隔离 Provider 细节、错误、速率限制 | core/provider_adapter (FakeAdapter, UppercaseAdapter) | core/provider_adapter/* | Implemented | core/provider_adapter/test_*.py | Real-provider adapters (auth/ratelimit) | High |
| REQ-006 | BOTH | Agent Runtime: 上下文加载、模型调用、工具调用、审计 | core/agent_runtime (AgentRuntime) | core/agent_runtime/* | Implemented | core/agent_runtime/test_*.py, core/e2e/test_e2e_flow.py | Multi-agent scheduling/coordination | High |
| REQ-007 | BOTH | AI Employee: 编排多个 Agents、KPI、报告 | Partial | core/agent_runtime + planner prototypes | Partial | core/e2e/test_e2e_flow.py (basic) | Full employee orchestration | High |
| REQ-008 | BOTH | Workflow Engine/Planner: Goal->Plan->Task Graph->Workflow | core/planner, core/task_graph, core/workflow | core/planner/* core/task_graph/* core/workflow/* | Implemented | core/e2e/test_e2e_flow.py, core/workflow/test_api.py | Planner heuristics, retries, long-running tasks | High |
| REQ-009 | BOTH | Tool Registry/Runtime: 注册、权限、沙箱、超时、重试 | Missing | - | Missing | - | Tool sandboxing & permission model | High |
| REQ-010 | BOTH | Memory: 分层、持久化、权限、隔离、版本 | Missing | - | Missing | - | Memory persistence and isolation | High |
| REQ-011 | BOTH | Knowledge/RAG Pipeline: 导入/解析/分块/索引/检索 | Missing | - | Missing | - | Ingestion, vector index, retrieval | High |
| REQ-012 | BOTH | Device Gateway/Robot: 设备接入、能力声明、适配器 | Missing | - | Missing | - | Device adapters & protocols | High |
| REQ-013 | BOTH | Security: Authentication/Authorization/Secrets/Encryption | core/secrets (SecretsManager prototype) | core/secrets/* | Partial | core/secrets/test_secrets.py | Master key persistence, RBAC, API auth | High |
| REQ-014 | BOTH | Observability: Logs/Metrics/Traces/Correlation ID | core/observability (traces/events, correlation_id, scrub) | core/observability/* | Implemented | core/observability/test_observability.py | Metrics export/centralization | High |
| REQ-015 | BOTH | Audit: Append-only、完整事件链路、审计存储 | Partial | model_gateway audit + observability traces | Partial | core/workflow/test_api.py shows trace persistence | High |
| REQ-016 | BOTH | CI/CD: 干净环境构建、测试、部署、健康检查 | .github/workflows/ci-core-tests.yml (unit) | .github/workflows/* | Partial | CI unit tests pass locally | Integration/e2e CI jobs missing | High |
| REQ-017 | BOTH | Privacy/Redaction/Data Routing: 数据分类与脱敏策略 | Partial | observability scrub implemented | Partial | core/observability/test_observability.py | Policy enforcement & routing | High |
| REQ-018 | BOTH | Supply Chain & Dependency Audit: 依赖审计与安全测试 | Missing | - | Missing | - | Dependency scanning & SBOM | Medium |
| REQ-019 | BOTH | E2E Acceptance: 完整链路从 Goal 到 Audit 的可执行测试（含真实 provider） | Partial | E2E using FakeAdapter + workflow API | Partial | core/e2e/test_e2e_flow.py, core/workflow/test_api.py | Real provider run requires API key | High |
| REQ-020 | BOTH | Documentation & Traceability: ADR、Capability Matrix、Gap Analysis | docs/* (traceability updated) | docs/Y1_REQUIREMENT_TRACEABILITY.md | Partial | docs exist but need expansion | High |

| REQ-001 | BOTH | Identity: 独立、稳定、加密凭证、恢复元数据 | core/identity (Identity, store, API) | core/identity/* | Partial | core/identity/test_*.py | Minor gaps: key management | High |
| REQ-002 | BOTH | Core: 管理 Identity/Context/Planning/Orchestration | core/core (Session, API) | core/core/* | Implemented | core/core/test_*.py | Needs scale/permissions | High |
| REQ-003 | BOTH | Model Gateway: 统一认证、路由、归一化、计费、审计 | core/model_gateway (routing + audit) | core/model_gateway/* | Implemented | core/model_gateway/test_*.py | Billing/normalization missing | High |
| REQ-004 | BOTH | Model Manager: 生命周期（发现/下载/验证/部署/回滚） | core/model_manager (lifecycle) | core/model_manager/* | Implemented | core/model_manager/test_*.py | Registry UI missing | High |
| REQ-005 | BOTH | Provider Adapter: 隔离 Provider 细节、错误、速率限制 | core/provider_adapter (Fake/Uppercase) | core/provider_adapter/* | Implemented | core/provider_adapter/test_*.py | Real provider integration pending | High |
| REQ-006 | BOTH | Agent Runtime: 上下文加载、模型调用、工具调用、审计 | core/agent_runtime (AgentRuntime) | core/agent_runtime/* | Implemented | core/agent_runtime/test_*.py | Multi-agent orchestration minimal | High |
| REQ-007 | BOTH | AI Employee: 编排多个 Agents、KPI、报告 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Employee Orchestration Test | 无实现 | High |
| REQ-008 | BOTH | Workflow Engine/Planner: Goal->Plan->Task Graph->Workflow | core/planner, core/task_graph, core/workflow | core/planner/* core/task_graph/* core/workflow/* | Implemented | core/e2e/test_e2e_flow.py | Planner heuristics need refinement | High |
| REQ-009 | BOTH | Tool Registry/Runtime: 注册、权限、沙箱、超时、重试 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Tool Permission & Risk Test | 无实现 | High |
| REQ-010 | BOTH | Memory: 分层、持久化、权限、隔离、版本 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Memory Persistence & Decoupling Test | 无实现 | High |
| REQ-011 | BOTH | Knowledge/RAG Pipeline: 导入/解析/分块/索引/检索 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Knowledge Persistence & RAG Tests | 无实现 | High |
| REQ-012 | BOTH | Device Gateway/Robot: 设备接入、能力声明、适配器 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Device & Robot Integration Tests | 无实现 | High |
| REQ-013 | BOTH | Security: Authentication/Authorization/Secrets/Encryption | core/secrets (SecretsManager prototype) | core/secrets/* | Partial | core/secrets/test_secrets.py | Key management, auth not complete | High |
| REQ-014 | BOTH | Observability: Logs/Metrics/Traces/Correlation ID | core/observability (traces/events, correlation_id, scrub) | core/observability/* | Implemented | core/observability/test_observability.py | Metrics/centralization pending | High |
| REQ-015 | BOTH | Audit: Append-only、完整事件链路、审计存储 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Audit Trail Tests | 无实现 | High |
| REQ-016 | BOTH | CI/CD: 干净环境构建、测试、部署、健康检查 | .github/workflows/ci-core-tests.yml (unit) | .github/workflows/* | Partial | CI unit tests pass locally | Full pipeline, integration missing | High |
| REQ-017 | BOTH | Privacy/Redaction/Data Routing: 数据分类与脱敏策略 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Data Routing & Redaction Tests | 无实现 | High |
| REQ-018 | BOTH | Supply Chain & Dependency Audit: 依赖审计与安全测试 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Dependency Audit Tests | 无实现 | Medium |
| REQ-019 | BOTH | E2E Acceptance: 完整链路从 Goal 到 Audit 的可执行测试 | Unknown | docs/MASTER_BLUEPRINT_Y1.md | Missing | Full E2E Run (Business Task) | 无实现 | High |
| REQ-020 | BOTH | Documentation & Traceability: ADR、Capability Matrix、Gap Analysis | docs/* (traceability updated) | docs/Y1_REQUIREMENT_TRACEABILITY.md | Partial | docs exist but need expansion | High |


后续步骤建议：
1. 将本文件提交为初始追踪表（现已写入 docs/）。
2. 依次对 REQ-001.. REQ-020 做细分任务并在 todos 表中记录（我可代为创建）。
3. 针对 Priority=High 的项优先开始实现 Phase 1/2 代码并编写相应测试。

---
生成者：Copilot CLI 自动生成初始追踪表模板（需人工或后续自动化逐条填充实现与证据）。
\n## Progress update: REQ-001 Identity\n- Current Implementation: identity module (core/identity/identity.py), sqlite persistence layer (core/identity/store.py), unit tests (core/identity/test_identity.py, core/identity/test_store.py).\n- Evidence: core/identity/identity.py, core/identity/store.py, core/identity/test_store.py, unit tests run OK.\n- Status: Partial\n- Test: Identity unit tests passed locally (5 tests).\n
\n## Progress update: REQ-002 Core\n- Current Implementation: core module (core/core/core.py) providing Session, Core manager integrating IdentityStore; unit tests (core/core/test_core.py) added.\n- Evidence: core/core/core.py, core/core/test_core.py.\n- Status: Partial\n- Test: Core unit tests passed locally as part of core test suite.\n
\n## Progress update: REQ-003 Model Gateway\n- Current Implementation: core/model_gateway/gateway.py providing routing and sqlite audit; unit tests (core/model_gateway/test_gateway.py) added.\n- Evidence: core/model_gateway/gateway.py, core/model_gateway/test_gateway.py; unit tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Model Gateway unit test passed as part of core test suite.\n
\n## Progress update: REQ-004 Model Manager\n- Current Implementation: core/model_manager/manager.py providing lifecycle methods (discover/download/verify/register/activate/rollback/remove).\n- Evidence: core/model_manager/manager.py, core/model_manager/test_manager.py; unit tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Model Manager unit test passed as part of core test suite.\n
\n## Progress update: REQ-005 Provider Adapter\n- Current Implementation: core/provider_adapter/adapter.py defining ProviderAdapter protocol and example adapters (FakeAdapter, UppercaseAdapter).\n- Evidence: core/provider_adapter/adapter.py, core/provider_adapter/test_adapter.py; unit tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Provider Adapter unit tests passed as part of core test suite.\n
\n## Progress update: REQ-006 Agent Runtime\n- Current Implementation: core/agent_runtime/agent.py implementing AgentRuntime that loads task context, selects provider adapter and delegates to ModelGateway; unit test core/agent_runtime/test_agent.py added.\n- Evidence: core/agent_runtime/agent.py, core/agent_runtime/test_agent.py; unit tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Agent Runtime unit test passed as part of core test suite.\n
\n## Progress update: REQ-001 Identity - API Completion\n- Current Implementation: Added HTTP API (core/identity/api.py) with endpoints: create, get, rotate; integration test core/identity/test_api.py added.\n- Evidence: core/identity/api.py, core/identity/test_api.py; integration unit tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Identity API integration test passed as part of core test suite.\n
\n## Progress update: REQ-002 Core Service\n- Current Implementation: Added lightweight HTTP API (core/core/api.py) exposing session management endpoints and integration tests (core/core/test_api.py).\n- Evidence: core/core/api.py, core/core/test_api.py; integration tests passed locally.\n- Status: Implemented (todo marked done)\n- Test: Core API integration test passed as part of core test suite.\n
