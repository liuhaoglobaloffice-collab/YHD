# Audit Record Example

## Audit Event

- event_id: audit-0001
- action: workflow.execution
- actor: system
- resource: workflow
- result: success
- tenant_id: tenant-a
- timestamp: 2026-08-26T00:00:00Z

## Integrity

Audit records are linked to the governance trace through a hash-chain-compatible event sequence.
