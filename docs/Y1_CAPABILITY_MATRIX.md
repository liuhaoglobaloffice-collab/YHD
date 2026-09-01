# LiuHao AI OS Y1 Capability Matrix

This matrix reflects the current repository state as of 2026-09-01. It intentionally separates implemented capability from simulated or interface-ready capability so that the team can make risk-based decisions without overstating completion.

Format: Capability | Maturity | Status | Evidence | Blocker

| Capability | Maturity | Status | Evidence | Blocker |
|---|---|---|---|---|
| Identity / Auth / RBAC | L3 | TESTED | `tests/auth/*`, `tests/security/*`, `src/identity/*`, `src/api/routes/auth.py` | - |
| Enterprise / Tenant / Owner model | L3 | TESTED | `src/identity/models.py`, `src/database/models.py`, productization tests | - |
| Backend API foundation | L3 | TESTED | `src/api/app.py`, `src/api/routes/*`, health checks | - |
| Readiness / security posture reporting | L3 | TESTED | `src/api/routes/health.py`, `src/security/secrets.py`, `tests/sre/test_production_secrets_hardening.py` | - |
| SQLite runtime compatibility / in-memory DB safety | L3 | TESTED | `src/database/base.py`, `src/api/dependencies/database.py`, health/startup regression checks | - |
| Frontend shell / routing / dashboard | L3 | TESTED | `frontend/src/**`, `frontend/package.json`, frontend build run | - |
| Provider abstraction | L3 | TESTED | `src/ai/providers.py`, `src/ai/gateway.py`, provider registration flow | - |
| Provider config persistence / tenant scoping | L3 | TESTED | `src/ai/provider_setup.py`, `src/api/routes/provider_status.py`, `tests/providers/test_provider_config.py` | - |
| Model registry / model management | L3 | TESTED | `src/ai/providers.py`, `src/ai/model_manager.py`, provider registry + active model switching tests | - |
| AI Agent orchestration | L2 | PARTIAL | `src/ai/agents.py`, `src/ai/orchestrator.py`, task execution flow | Advanced policy, escalation, and agent memory still incomplete |
| AI Employee / workforce | L2 | PARTIAL | `src/workforce/*`, `src/api/routes/workforce.py` | Full tenant-owner lifecycle and runtime execution are still incomplete |
| Task system | L3 | TESTED | `src/tasks/*`, `tests/integration/test_task_executor.py` | - |
| Workflow engine | L3 | TESTED | `src/workflow/*`, `tests/workflow/*`, `tests/integration/test_workflow_executor.py` | - |
| Goal-to-task business loop | L2 | PARTIAL | `src/goal*`, workflow and executor integration | Not fully closed with verification and audit trail across all scenarios |
| Memory | L2 | PARTIAL | `src/knowledge/memory.py`, related memory services | Not fully integrated into a real enterprise memory graph |
| Knowledge / document retrieval | L2 | PARTIAL | `src/knowledge/knowledge_retrieval.py`, `src/api/routes/knowledge.py`, `tests/knowledge/test_rag_pipeline.py` | Repository-backed retrieval and semantic quality are not yet production-grade |
| Knowledge import / parse / chunk / index / retrieve | L2 | PARTIAL | document processing and retrieval services | File-type coverage and indexing quality still limited |
| Communication gateway | L1 | INTERFACE_READY | `src/integrations/*`, communication routes | No legal third-party authorization for real messaging/email/chat channels |
| Translation layer | L1 | INTERFACE_READY | translation abstractions and adapters | No verified production language provider integration |
| Device gateway | L1 | INTERFACE_READY | device abstraction layer and routing | Real platform/hardware permission not available in this environment |
| Watch endpoint | L1 | SIMULATED | watch gateway abstractions and simulator patterns | No real wearable SDK / hardware |
| Robot / Machine Duck | L1 | SIMULATED | robot device and simulator scaffolding | No real hardware / robot SDK |
| Desktop app shell | L1 | PLANNED | frontend shell and packaging scaffolds | Native desktop packaging not yet validated |
| Mobile app shell | L1 | PLANNED | mobile architecture scaffolds | iOS/Android signing and platform approval required |
| Security / governance / audit | L3 | TESTED | `src/security/*`, `src/identity/audit.py`, audit-related tests | - |
| Observability / logs / tracing | L2 | PARTIAL | logging + startup lifecycle + health endpoints | Not yet full distributed observability stack |
| Cost / budget / usage accounting | L2 | PARTIAL | cost trackers and budget controls | Real ROI and optimization loop still missing |
| Compliance / secret handling | L3 | TESTED | `.env.example`, secret/environment separation, audit flows | - |
| Business workflow automation | L2 | PARTIAL | workflow templates and API routes | End-to-end goal business execution is not fully verified in production-like conditions |
| Production readiness | L2 | PARTIAL | tests + build + app startup pass in development | Requires real provider credentials, broader integration validation, and operational hardening |

## Summary

The repo is no longer a blank scaffold. It has a solid foundation and multiple L3 capabilities, including auth, workflow, tasks, provider configuration, and frontend shell. However, the system is still not a full Y1 production-capable OS because several key end-to-end loops are only partially integrated or remain simulator-only under real external dependency constraints.

## Assessment

The highest-confidence real capabilities are in the core platform foundation and action engine. The main gaps remain in the final autonomous loops: verified business outcomes, full knowledge retrieval quality, end-to-end workflow verification, and real external integration under legal authorization.
