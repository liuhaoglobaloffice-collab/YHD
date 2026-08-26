# Data Lifecycle Policy

## Data Classification

The enterprise platform classifies data into four major categories:

1. Enterprise public data
2. Internal business data
3. Sensitive data
4. High-risk data

## Lifecycle

Data enters the platform through the enterprise knowledge ingestion or workflow intake path. It is stored in the knowledge, task, audit, workflow, or provider metadata surfaces subject to the tenant and RBAC context. It is then used only through approved workflow, RAG, and security-aware retrieval policies. During storage and use, data ownership, access scope, PII masking, and secret-handling rules must be enforced. After a defined retention period, data is archived, then finally deleted under enterprise data governance controls.

## Rules

- Retention period: business default is 365 days; high-risk and regulated data requires a shorter or specially reviewed retention cycle.
- Deletion method: data should be deleted through structured data-disposal workflow with an audit record for its removal.
- Data owner: enterprise data owner or business owner assigned by tenant.
- Access: access must be checked against tenant validation, RBAC, ABAC, and PII rules.

## Governance Connection

This policy connects the Phase 2 Knowledge Brain surface, the Phase 5 security governance surface, and Phase 8 operations reporting.
