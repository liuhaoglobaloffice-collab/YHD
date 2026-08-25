# LiuHao AI OS Module Status

## 1. Core Production Modules

These modules are the current production backbone of the platform and should stay enabled unless a specific operational issue is identified.

| Module | Current status | Production enabled | Recommendation |
| --- | --- | --- | --- |
| api | Stable | Yes | Keep enabled and treat as the primary external integration surface. |
| core | Stable | Yes | Keep enabled; config, lifecycle, and error handling remain foundational. |
| identity | Stable | Yes | Keep enabled; auth and RBAC are prerequisite for platform access. |
| database | Stable | Yes | Keep enabled; used by all domain services and release validation. |
| business | Stable | Yes | Keep enabled; supplier and operational business logic are the clearest value layer. |
| supplier | Production-grade | Yes | Keep enabled; this is the strongest business-capable domain in the current codebase. |
| tasks | Operational | Yes | Keep enabled; task orchestration is required for workflows and operational automation. |
| workflow | Operational | Yes | Keep enabled; workflow engine is a key platform primitive for orchestration. |
| ai | Controlled rollout | Yes | Keep enabled in controlled mode; provider abstractions should be validated before broad expansion. |

## 2. Experimental Modules

These modules are valuable but still need hardening before being treated as guaranteed production components.

| Module | Current status | Production enabled | Recommendation |
| --- | --- | --- | --- |
| workforce | Experimental | No | Keep behind feature gates; validate ownership, orchestration, and escalation flows before enabling in production. |
| jarvis | Experimental | No | Keep isolated; voice interaction and command handling remain useful but not release-critical. |
| ceo | Experimental | No | Keep as a strategic dashboard module; continue validation through controlled demos before production activation. |

## 3. Paused Modules

These modules are intentionally not active for the current release and should remain off until they are fully validated.

| Module | Current status | Production enabled | Recommendation |
| --- | --- | --- | --- |
| knowledge | Paused | No | Keep disabled until retrieval quality, indexing, and governance are validated. |
| supplier_risk | Paused | No | Keep disabled until supplier-risk scoring and approval logic are fully tested against real business scenarios. |

## 4. Operational Summary

- The current release should focus on the production backbone: api, core, identity, database, business, supplier, tasks, workflow, and ai.
- Experimental modules should remain off from the default production path.
- Paused modules should not be registered or enabled until they pass targeted validation and readiness review.
- No module should be treated as production-ready solely because it exists in the code tree; activation requires validation and operational signoff.
