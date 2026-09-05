# LIUHAO X v3.0 — Kernel Foundation Status

This document records the first concrete implementation slice from the v3.0 Definition Lock.

## Implemented in this phase

- Unified principal identity model with explicit owner requirements for agents/sub-agents.
- Principal lifecycle: active, suspended, revoked, terminated.
- Capability registry with explicit principal grants.
- Deterministic policy engine with `ALLOW`, `DENY`, and `REQUIRE_APPROVAL` outcomes.
- Default-deny policy posture when no rule matches.
- Kernel authorization facade combining identity + capability + policy.
- Append-only in-process kernel event store for authorization/audit evidence.
- Security-focused unit tests covering identity, capability, policy, and denial behavior.

## Explicitly not claimed as complete

The repository baseline is currently a metrics persistence starter, not a complete Agent OS. The following are not yet production-complete and remain phase-gated:

- PostgreSQL/SQLAlchemy persistence for kernel entities.
- FastAPI HTTP surface for kernel APIs.
- Durable event bus / audit storage.
- Agent process runtime, scheduler, checkpoints, and recovery.
- Model gateway/router.
- Memory and context kernels.
- Tool sandboxing and world interfaces.
- Multi-agent orchestration, organization, network, governance, economy, and L10K.

Status for this slice: `PARTIALLY_IMPLEMENTED` at system level; the individual in-process primitives are implemented and tested, but are not yet the production platform boundary described by v3.0.

## Acceptance rule

No higher layer should introduce a parallel identity, capability, policy, or audit implementation. Subsequent phases must build on `src/kernel` and replace only its storage/execution adapters while keeping these domain contracts authoritative.
