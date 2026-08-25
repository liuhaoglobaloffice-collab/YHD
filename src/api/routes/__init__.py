"""
API routes initialization
"""

from fastapi import APIRouter

from src.api.routes import (
    ai_brain,  # Phase 3.1 - AI Brain Core
    approvals,
    audit,
    auth,
    business,  # Stage 7
    ceo,  # Stage 8
    dashboard,  # Week 2 Day 4 - Dashboard API
    health,
    jarvis,  # Jarvis Voice Interaction
    permissions,
    providers,
    rag,  # Week 4 - RAG System
    roles,
    metrics,
    # knowledge,  # TODO: Fix initialization in Stage 4
    supplier,  # Module 48 - Supplier Intelligence
    tasks,
    users,
    workflows,
    workforce,  # Stage 6
)

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include route modules
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(providers.router)
api_router.include_router(approvals.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)  # Week 2 Day 4
# api_router.include_router(knowledge.router)  # Stage 4 remains intentionally disabled
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(workforce.router)  # Stage 6
api_router.include_router(business.router)  # Stage 7
api_router.include_router(supplier.router)  # Module 48 - Supplier Intelligence
api_router.include_router(ceo.router)  # Stage 8
api_router.include_router(ai_brain.router)  # Phase 3.1 - AI Brain Core
api_router.include_router(jarvis.router)  # Jarvis Voice Interaction
api_router.include_router(rag.router)  # Week 4 - RAG System

# metrics endpoint (prometheus text) is mounted at /metrics (root path)
from src.api.routes import metrics as _metrics_module
api_router.include_router(_metrics_module.router)

__all__ = ["api_router"]
