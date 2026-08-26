# AI Governance Policy

## AI Use Rules

AI Agents must operate only within an approved permission range. Automated execution must not perform unsafe actions without a human approval gate for high-impact actions such as supplier changes, high-risk customer decisions, model changes, or workflow promotion events. AI output must be recorded and traced through the audit path.

## Model Governance

- Model source must be tracked in the model registry.
- Model version must be stored with the model lifecycle record.
- Model changes must be logged with experiment, dataset, and deployment metadata.
- Each model update must pass a risk review and be recorded in the audit system.

## Output Governance

- AI outputs must be reviewable and linked to task and workflow objects.
- High-risk recommendations require explicit human confirmation.
- Audit traceability must be preserved for all AI output and decision artifacts.

## Connections

This policy connects Phase 4 MLOps, Phase 5 security, and the governance dashboard.
