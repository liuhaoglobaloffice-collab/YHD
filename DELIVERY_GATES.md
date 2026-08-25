# Final delivery gates

This document defines the go/no-go gates for moving beyond the current runtime baseline and continuing with broader feature work.

## P0: blocking gates

These must all pass before any feature expansion continues.

### 1. Real staging validation
- Requirement: `STAGING_DATABASE_URL` is configured in GitHub Secrets.
- Check: the workflow `Verify Metrics Persistence` connects to the real staging DB.
- Success criteria:
  - `DATABASE_URL` resolves to the staging DB, not SQLite fallback
  - the script inserts a sample row successfully
  - the query reads the row back successfully
  - output shows `persisted_rows > 0`
- Fail condition:
  - workflow falls back to SQLite without warning
  - no real staging endpoint is used

### 2. Runtime health and readiness
- Requirement: app exposes stable health and readiness endpoints or equivalents.
- Check:
  - `health()` returns a valid status payload
  - `ready()` returns a valid readiness payload
  - startup/shutdown lifecycle does not fail silently
- Success criteria:
  - `status` is stable and meaningful
  - `database_url` is defined
  - `provider_samples` is available and queryable

### 3. Data-write path is real
- Requirement: provider metrics follow a single real path from collection to persistence to readback.
- Check:
  - sample is inserted using the application repository or equivalent runtime code
  - data is queryable in the same DB
- Success criteria:
  - no reliance on ad hoc scripts for normal runtime behavior
  - readback confirms live data

### 4. Environment configuration is explicit
- Requirement: all required variables are known and documented.
- Required keys:
  - `APP_ENV`
  - `DATABASE_URL`
  - `STAGING_DATABASE_URL`
  - `SECRET_KEY`
  - `JWT_SECRET`
  - `LOG_LEVEL`
  - `METRICS_PERSIST`
- Success criteria:
  - startup does not depend on hidden local state
  - environment documentation matches runtime behavior

## P1: required before productization

### 1. API contract
- Requirement: request/response contracts are explicit and stable.
- Must include:
  - `GET /health`
  - `GET /ready`
  - `GET /metrics`
  - `POST /metrics/provider`
- Success criteria:
  - input/output schema is clear
  - error responses are consistent
  - contract is documented and testable

### 2. Migration baseline
- Requirement: schema versioning exists and is repeatable.
- Confirm:
  - migration SQL is tracked in source control
  - migration can be executed in the target DB
  - schema creation is reproducible
- Success criteria:
  - a fresh environment can be initialized without manual drift

### 3. Test coverage and regression safety
- Must cover:
  - smoke
  - persistence round-trip
  - health/readiness
  - lifecycle/startup
- Success criteria:
  - tests pass in CI
  - runtime contract stays stable through changes

### 4. Runbook and handoff docs
- Requirement: a newcomer can run the project without hidden notes.
- Success criteria:
  - setup steps are documented
  - secrets and DB config are spelled out
  - common failures and recovery steps are known

## P2: optimization and expansion

These are not blocking for the current baseline, but should be scheduled after P0/P1 passes.

- monitoring and alerts
- latency and error trends
- rollback plan
- deployment health checks
- frontend/product polish
- broader module expansion

## Go / No-go rule

Go only when all P0 gates pass and the majority of P1 items are complete.

No-go if any of the following is true:
- real staging DB is not configured
- SQLite fallback is treated as production evidence
- health or readiness is not stable
- migration is not reproducible
- environment variables are undocumented or hidden

## Immediate next action

1. Configure `STAGING_DATABASE_URL` in GitHub Secrets.
2. Trigger the `Verify Metrics Persistence` workflow.
3. Confirm the workflow uses the staging DB and not SQLite fallback.
4. Ensure all P0 checks pass.
5. Only then resume broader feature development.
