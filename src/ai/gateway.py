"""Provider Gateway singleton for the application.

Central access point for the ProviderGateway used by AgentRuntime
and other components. Initialized during application startup.
"""

import logging
from typing import Optional

from .providers import ProviderGateway

logger = logging.getLogger(__name__)

_gateway: Optional[ProviderGateway] = None


def get_gateway() -> ProviderGateway:
    """Get the global ProviderGateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = ProviderGateway()
        logger.info("Provider Gateway singleton created")
    return _gateway


def set_gateway(gateway: ProviderGateway) -> None:
    """Set the global ProviderGateway singleton (used during startup)."""
    global _gateway
    _gateway = gateway
    logger.info("Provider Gateway singleton set")


def reset_gateway() -> None:
    """Reset the ProviderGateway singleton (for testing)."""
    global _gateway
    _gateway = None