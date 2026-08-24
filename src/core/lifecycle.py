"""
Layer 0: Core Runtime
Application lifecycle management
"""

from contextlib import asynccontextmanager
from typing import Optional

import structlog

from src.core.config import get_settings
from src.core.events import Event, get_event_bus
from src.core.logging import configure_logging

logger = structlog.get_logger(__name__)


class LifecycleManager:
    """
    Manages application startup and shutdown lifecycle
    Ensures proper initialization order and cleanup
    """

    def __init__(self):
        self._started = False
        self._stopped = False
        self.settings = None
        self.event_bus = None

    async def startup(self) -> None:
        """Initialize all core systems"""
        if self._started:
            logger.warning("lifecycle_startup_already_called")
            return

        logger.info("lifecycle_startup_begin")

        try:
            # 1. Load configuration
            self.settings = get_settings()
            logger.info(
                "configuration_loaded",
                env=self.settings.app_env,
                debug=self.settings.app_debug,
            )

            # 2. Configure logging
            configure_logging()
            logger.info("logging_configured", level=self.settings.log_level)

            # 3. Initialize event bus
            self.event_bus = get_event_bus()
            logger.info("event_bus_initialized")

            # 4. Publish startup event
            self.event_bus.publish(
                Event(
                    name="system.startup",
                    data={"env": self.settings.app_env},
                    source="lifecycle_manager",
                )
            )

            self._started = True
            logger.info("lifecycle_startup_complete")

        except Exception as e:
            logger.error("lifecycle_startup_failed", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Clean shutdown of all systems"""
        if self._stopped:
            logger.warning("lifecycle_shutdown_already_called")
            return

        logger.info("lifecycle_shutdown_begin")

        try:
            # Publish shutdown event
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        name="system.shutdown",
                        data={},
                        source="lifecycle_manager",
                    )
                )

            # Clean up resources
            # (Database connections, Redis, etc. will be added in future stages)

            self._stopped = True
            logger.info("lifecycle_shutdown_complete")

        except Exception as e:
            logger.error("lifecycle_shutdown_failed", error=str(e))
            raise

    def is_ready(self) -> bool:
        """Check if system is ready to serve requests"""
        return self._started and not self._stopped


# Global lifecycle manager
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get global lifecycle manager (Singleton)"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


@asynccontextmanager
async def lifespan_context():
    """
    Async context manager for application lifecycle
    Use with FastAPI lifespan parameter
    """
    manager = get_lifecycle_manager()
    await manager.startup()
    try:
        yield
    finally:
        await manager.shutdown()
