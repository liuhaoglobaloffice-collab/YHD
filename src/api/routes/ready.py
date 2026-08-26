"""
Readiness endpoint
Provides /ready endpoint under /api/v1/ready
"""

from fastapi import APIRouter
from src.core.lifecycle import get_lifecycle_manager

router = APIRouter()


@router.get("/ready")
async def ready():
    lifecycle = get_lifecycle_manager()
    status = "ready" if lifecycle.is_ready() else "not_ready"
    return {"status": status}
