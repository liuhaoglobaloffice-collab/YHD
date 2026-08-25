"""
Layer 0: Core Runtime
Event Bus for decoupled communication
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Standard event types"""

    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"

    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_ASSIGNED = "task.assigned"

    # Workflow events
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_UPDATED = "workflow.updated"
    WORKFLOW_DELETED = "workflow.deleted"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    WORKFLOW_CANCELLED = "workflow.cancelled"

    # Knowledge events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_INDEXED = "document.indexed"

    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    APPROVAL_CANCELLED = "approval.cancelled"


@dataclass
class Event:
    """Event data structure"""

    name: str
    data: Dict[str, Any]
    timestamp: datetime = None
    source: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


# Type aliases for event handlers
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]  # Returns awaitable


class EventBus:
    """
    Internal event bus for decoupled module communication
    Thread-safe and supports both sync and async handlers
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._async_handlers: Dict[str, List[AsyncEventHandler]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Subscribe to an event (synchronous handler)"""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
        logger.info("event_subscribed", event_name=event_name, handler=handler.__name__)

    def subscribe_async(self, event_name: str, handler: AsyncEventHandler) -> None:
        """Subscribe to an event (asynchronous handler)"""
        if event_name not in self._async_handlers:
            self._async_handlers[event_name] = []
        self._async_handlers[event_name].append(handler)
        logger.info("event_subscribed_async", event_name=event_name, handler=handler.__name__)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Unsubscribe from an event"""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
                logger.info("event_unsubscribed", event_name=event_name, handler=handler.__name__)
            except ValueError:
                pass

    def unsubscribe_async(self, event_name: str, handler: AsyncEventHandler) -> None:
        """Unsubscribe from an async event"""
        if event_name in self._async_handlers:
            try:
                self._async_handlers[event_name].remove(handler)
                logger.info(
                    "event_unsubscribed_async", event_name=event_name, handler=handler.__name__
                )
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """Publish an event (synchronous)"""
        logger.info("event_published", event_name=event.name, source=event.source)

        # Execute sync handlers
        if event.name in self._handlers:
            for handler in self._handlers[event.name]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        "event_handler_error",
                        event_name=event.name,
                        handler=handler.__name__,
                        error=str(e),
                    )

    async def publish_async(self, event: Event) -> None:
        """Publish an event (asynchronous)"""
        logger.info("event_published_async", event_name=event.name, source=event.source)

        # Execute sync handlers (in background)
        if event.name in self._handlers:
            for handler in self._handlers[event.name]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        "event_handler_error",
                        event_name=event.name,
                        handler=handler.__name__,
                        error=str(e),
                    )

        # Execute async handlers
        if event.name in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event.name]:
                tasks.append(self._execute_async_handler(handler, event))
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_async_handler(self, handler: AsyncEventHandler, event: Event) -> None:
        """Execute async handler with error handling"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "async_event_handler_error",
                event_name=event.name,
                handler=handler.__name__,
                error=str(e),
            )

    def clear(self) -> None:
        """Clear all handlers (for testing)"""
        self._handlers.clear()
        self._async_handlers.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance (Singleton)"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset event bus (for testing only)"""
    global _event_bus
    if _event_bus is not None:
        _event_bus.clear()
    _event_bus = None
