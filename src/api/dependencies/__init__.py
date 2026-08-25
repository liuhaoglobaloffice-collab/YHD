"""
API Dependencies - Phase 2F

Provides reusable FastAPI dependencies for:
- Database session management
- Authentication (get_current_user)

Import patterns:
    # Database (from this package)
    from src.api.dependencies import get_db

    # Auth (re-exported from parent module)
    from src.api.dependencies import get_current_user
"""

import importlib.util

# Import auth functions from parent dependencies.py module
# This requires some import magic to avoid circular dependencies
from pathlib import Path

from .database import (
    close_database,
    get_async_session_dependency,
    get_db,
    get_db_session,
    init_database,
)

# Load parent dependencies.py as a module
_parent_deps_path = Path(__file__).parent.parent / "dependencies.py"
spec = importlib.util.spec_from_file_location("src.api._dependencies_module", _parent_deps_path)
_parent_deps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_parent_deps)

# Re-export auth functions
get_current_user = _parent_deps.get_current_user
get_current_user_optional = _parent_deps.get_current_user_optional
require_permission_dependency = _parent_deps.require_permission_dependency  # For Permission enum

# Service dependencies
get_employee_registry = _parent_deps.get_employee_registry
get_business_task_registry = _parent_deps.get_business_task_registry
get_employee_service = _parent_deps.get_employee_service
get_business_service = _parent_deps.get_business_service

# Import permission functions
from .permissions import require_admin, require_any_permission, require_permission

__all__ = [
    # Database
    "get_async_session_dependency",
    "get_db",
    "get_db_session",
    "init_database",
    "close_database",
    # Auth
    "get_current_user",
    "get_current_user_optional",
    "require_permission_dependency",
    # Permissions
    "require_permission",
    "require_any_permission",
    "require_admin",
    # Services
    "get_employee_registry",
    "get_business_task_registry",
    "get_employee_service",
    "get_business_service",
]
