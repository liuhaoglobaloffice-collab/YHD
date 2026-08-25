# Staging verification checklist

This repository is not considered staging-validated until the following items pass in a real staging environment.

## Required GitHub secret
- `STAGING_DATABASE_URL`

## Checklist
1. Set `STAGING_DATABASE_URL` to a reachable staging database.
2. Ensure the target database accepts PostgreSQL or the expected DB driver.
3. Run the `Verify Metrics Persistence` workflow.
4. Confirm the workflow output includes `persisted_rows > 0`.
5. Confirm the DB query returns recent rows from `provider_metric_samples`.
6. Confirm the result came from the staging DB and not the SQLite fallback.
7. Only then classify the project as staging-validated.

## Failure condition
If `STAGING_DATABASE_URL` is unset, the workflow must fail instead of silently using SQLite. This is a hard reminder that SQLite success is not staging proof.
