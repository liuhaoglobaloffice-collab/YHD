"""
Dependency Injection Container

Simple service registry for dependency management.
"""

from typing import Any, Dict, Optional, Type, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Global service registry
_services: Dict[Type, Any] = {}


def register_service(service_type: Type[T], instance: T) -> None:
    """
    Register a service instance.

    Args:
        service_type: Service class type
        instance: Service instance
    """
    _services[service_type] = instance
    logger.info("service_registered", service_type=service_type.__name__)


def get_dependency(service_type: Type[T]) -> Optional[T]:
    """
    Get service instance by type.

    Args:
        service_type: Service class type

    Returns:
        Service instance or None if not registered
    """
    instance = _services.get(service_type)

    if instance is None:
        # Try to create instance if not registered
        # This allows lazy initialization
        try:
            instance = service_type()
            register_service(service_type, instance)
            logger.info("service_auto_created", service_type=service_type.__name__)
        except Exception as e:
            logger.warning(
                "service_creation_failed", service_type=service_type.__name__, error=str(e)
            )
            return None

    return instance


def clear_services() -> None:
    """Clear all registered services (for testing)."""
    _services.clear()
    logger.info("services_cleared")


def list_services() -> Dict[str, Any]:
    """List all registered services."""
    return {svc_type.__name__: instance for svc_type, instance in _services.items()}
