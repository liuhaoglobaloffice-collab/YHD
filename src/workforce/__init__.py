"""
AI Workforce Layer - External AI Employee Management.

Stage 6: External AI Workforce
Layer: AI Employee Identity System

Enforces:
- AI Employee ≠ Agent (Employees are business entities, agents are runtime)
- AI Employee ≠ Workflow (Employees execute through workflows)
- Security First, Approval First, Fail Closed
- RBAC Integration
- Audit Everything
- Single Source of Truth
"""

from .models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    Position,
)

# Services not exported - import directly to avoid circular imports

__all__ = [
    "AIEmployee",
    "AIEmployeeStatus",
    "Department",
    "Position",
]
