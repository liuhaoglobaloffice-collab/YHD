# LiuHao-AI-OS

Minimal provider metrics persistence starter for the AI platform runtime.

## What this repo contains
- `src/api/providers_metrics.py` — SQLite-backed provider metrics repository.
- `src/api/providers_metrics_persist.py` — sample persistence helper.
- `src/api/app.py` — small application factory/state object.
- `src/core/lifecycle.py` — startup/shutdown lifecycle manager.
- `scripts/verify_metrics_persist.py` — end-to-end persistence verification script.

## Required environment variables

```bash
APP_ENV=staging
DATABASE_URL=sqlite:///./verify_metrics.db
STAGING_DATABASE_URL=postgresql://user:password@host:5432/app_db
SECRET_KEY=replace-me
JWT_SECRET=replace-me
LOG_LEVEL=INFO
METRICS_PERSIST=1
```

## Local verification

```bash
export METRICS_PERSIST=1
export DATABASE_URL=sqlite:///./verify_metrics.db
python scripts/verify_metrics_persist.py
```

## Health baseline

```bash
python -c "from src.api.app import MetricsApplication; print(MetricsApplication().health())"
```

## P0 execution checklist

1. Configure real `STAGING_DATABASE_URL` in GitHub Secrets.
2. Trigger the `verify_metrics_persist` workflow.
3. Verify insert + read succeeds on staging, not just SQLite.
4. Confirm startup/status/health all return a valid service state.
5. Only then move to P1 API contract and migration work.

## P1 runtime contract

Minimal API contract for the service baseline:

- `health()` -> returns a service health payload with `status`, `database_url`, and `provider_samples`
- `ready()` -> returns a readiness payload with `status`, `database_url`, and `provider_samples`
- `list_metrics(limit)` -> returns recent metrics rows
- `record_metric(provider, model, latency_ms, success_rate)` -> writes a new metric row

These are the runtime primitives that must exist before broader feature work continues.

## Database migration baseline

The project now includes a migration script at `migrations/001_create_provider_metric_samples.sql`.

Apply it in a real environment with the database client for that environment, for example:

```bash
sqlite3 verify_metrics.db < migrations/001_create_provider_metric_samples.sql
```

For PostgreSQL or other managed DBs, run the same SQL statements in the target database using the environment's migration tool or SQL client.

## Staging gate

This project is not staging-validated unless `STAGING_DATABASE_URL` is configured and the workflow proves the target database receives and returns rows.

See `STAGING_CHECKLIST.md` for the exact validation gate and `DELIVERY_GATES.md` for the full go/no-go checklist.

## CLI entrypoint

You can exercise the runtime directly without additional dependencies:

```bash
python main.py health
python main.py ready
python main.py startup
python main.py record --provider openai --model gpt-4o-mini --latency-ms 220.5 --success-rate 0.99
```

## Test run

```bash
pytest -q
```
