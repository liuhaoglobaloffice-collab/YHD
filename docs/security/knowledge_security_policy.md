# Knowledge Security Policy

## Data classification

The repository security model should treat enterprise knowledge content as a data-classification ladder:

- Public: open documentation, external product descriptions, approved public release notes.
- Internal: internal workflow knowledge, engineering handbooks, operational documents.
- Confidential: supplier information, customer relationship information, and internal business documents that are not public.
- Restricted: credentials, PII, supplier details, customer records, security classifications, or any record with legal/compliance controls.

## PII handling policy

PII must be detected, masked, blocked, or audited depending on document and retrieval context.

Supported detection rules:

- Email: detect with a rule-based pattern and mask to `[REDACTED]`.
- Phone: detect with a phone number pattern and mask to `[REDACTED]`.
- Address: detect address and location markers, then route to a flagged policy evaluation.
- Identity information: detect identifiers, passports, SSNs, and equivalent tokens.
- Customer / supplier information: flag records that mention customer or supplier contact elements.

Rules:

- Detect: run `detect_pii()` to identify a text span.
- Mask: run `KnowledgeSecurityPolicy.filter_content()` before output is returned.
- Block: deny retrieval if a document owner/company scope does not match the user.
- Audit: log `security_status`, `pii_detected`, `filtered`, `policy_version`, and provider metadata.

## Document access policy

Every retrieved document should carry minimal metadata:

- document owner
- company scope
- user permission
- retrieval permission

The prototype policy enforces a lightweight owner and company-scope validation in `validate_retrieval()` while preserving the current architecture.

## Retrieval security

Every knowledge search or query should record the following metadata in an audit event:

- user
- query
- retrieved documents
- timestamp
- provider
- result status

## LLM output security

The LLM answer path must enforce:

- sensitive information leakage prevention
- unsafe response filtering
- audit requirement

The implementation begins with a deterministic post-generation filter and posts a structured security event/metadata payload in the RAG pipeline.
