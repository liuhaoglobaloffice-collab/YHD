"""
API Service Factories

Phase 2F-2.5: Service Factory Architecture

Provides dependency injection factories for all services.
Ensures consistent service instantiation across API layer.

Architecture:
    Dependency Injection
        ↓
    Service Factory
        ↓
    Service(session, registry, rbac, audit)
        ↓
    Repository Layer
        ↓
    Database

Factories handle:
- AsyncSession injection
- Registry instantiation
- RBAC service creation
- Audit service integration
- Transaction management
"""

from .business import get_business_service
from .knowledge import get_company_brain, get_document_service, get_memory_service
from .task import get_task_service
from .workflow import get_workflow_service
from .workforce import get_workforce_service

__all__ = [
    "get_business_service",
    "get_workflow_service",
    "get_task_service",
    "get_workforce_service",
    "get_document_service",
    "get_memory_service",
    "get_company_brain",
]
