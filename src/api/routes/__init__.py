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
    crm,  # S3 - Acquisition & CRM
    dashboard,  # Week 2 Day 4 - Dashboard API
    health,
    imports,  # S1 - Data import
    inbox,  # S2 - Unified inbox
    jarvis,  # Jarvis Voice Interaction
    meetings,  # Weekly Meeting Chat
    permissions,
    platforms,  # S2 - Multi-platform integration
    productization,
    quotes,  # P3f - Quotation Management
    rag,  # Week 4 - RAG System
    ready,  # readiness endpoint
    roles,
    knowledge,  # Stage 4 - Knowledge Management
    market,  # S5 - AI Employee Market & Evolution
    site,  # S4 - Website & SEO
    supplier,  # Module 48 - Supplier Intelligence
    supplier_risk,  # Risk assessment route module for supplier flow
    tasks,
    templates,  # S2 - Message templates
    users,
    system,  # S6 - System overview & monitoring
    webhooks,  # S2 - Platform webhooks
    workflows,
    workforce,  # Stage 6
    accounts,  # S1 - Sub-account management
    products,  # P3c - Product Catalog
    goals,  # P1 - CEO Goal Center
)

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include route modules
api_router.include_router(health.router)
api_router.include_router(ready.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(approvals.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)  # Dashboard Statistics (overview + system-health)
api_router.include_router(knowledge.router)  # Stage 4 - Knowledge Management
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(workforce.router)  # Stage 6
api_router.include_router(accounts.router)  # S1 - Sub-account management
api_router.include_router(imports.router)  # S1 - Data import
api_router.include_router(platforms.router)  # S2 - Multi-platform integration
api_router.include_router(templates.router)  # S2 - Message templates
api_router.include_router(inbox.router)  # S2 - Unified inbox
api_router.include_router(webhooks.router)  # S2 - Platform webhooks
api_router.include_router(business.router)  # Stage 7
api_router.include_router(supplier.router)  # Module 48 - Supplier Intelligence
api_router.include_router(supplier_risk.router)  # Supplier risk assessment route hookup
api_router.include_router(ceo.router)  # Stage 8
api_router.include_router(crm.router)  # S3 - Acquisition & CRM
api_router.include_router(site.router)  # S4 - Website & SEO
api_router.include_router(market.router)  # S5 - AI Employee Market & Evolution
api_router.include_router(ai_brain.router)  # Phase 3.1 - AI Brain Core
api_router.include_router(jarvis.router)  # Jarvis Voice Interaction
api_router.include_router(meetings.router)  # Weekly Meeting Chat
api_router.include_router(rag.router)  # Week 4 - RAG System
api_router.include_router(productization.router)
api_router.include_router(system.router)  # S6 - System overview & monitoring
api_router.include_router(products.router)  # P3c - Product Catalog
api_router.include_router(quotes.router)  # P3f - Quotation Management
api_router.include_router(goals.router)  # P1 - CEO Goal Center

__all__ = ["api_router"]
