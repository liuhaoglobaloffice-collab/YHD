"""
AI Employee Async Execution Queue.

Runs AI employee tasks in the background as asyncio tasks so that long-running
LLM calls do not block HTTP requests. Clients submit a task, get a task_id,
then poll GET /workforce/tasks/{task_id} for status.

Execution records are held in-memory (process-local). A future enhancement can
swap this for a durable store (DB table / Redis).
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionRecord:
    """In-memory record for a queued/running/completed AI task."""

    task_id: str
    employee_id: str
    employee_name: str
    agent_type: str
    prompt: str
    status: ExecutionStatus = ExecutionStatus.QUEUED
    output: str = ""
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 用于支持取消
    _cancel_event: Optional[asyncio.Event] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "agent_type": self.agent_type,
            "prompt": self.prompt,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_ms": round((self.completed_at or time.time()) - self.created_at, 3) * 1000
                if self.started_at else None,
            "metadata": self.metadata,
        }


class ExecutionQueue:
    """Process-local async task queue for AI employee executions."""

    def __init__(self, max_history: int = 200):
        self._tasks: Dict[str, ExecutionRecord] = {}
        self._asyncio_tasks: Dict[str, asyncio.Task] = {}
        self._max_history = max_history
        logger.info("execution_queue_initialized")

    async def submit(
        self,
        employee_id: UUID,
        employee_name: str,
        agent_type: str,
        prompt: str,
        run_fn,
    ) -> ExecutionRecord:
        """Create a record and schedule the background execution."""
        record = ExecutionRecord(
            task_id=str(uuid4()),
            employee_id=str(employee_id),
            employee_name=employee_name,
            agent_type=agent_type,
            prompt=prompt,
        )
        self._tasks[record.task_id] = record

        # 修剪历史
        if len(self._tasks) > self._max_history:
            # 保留最近的 max_history 条
            completed_keys = [
                k for k, v in self._tasks.items()
                if v.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED)
            ]
            for key in completed_keys[: len(self._tasks) - self._max_history]:
                self._tasks.pop(key, None)
                self._asyncio_tasks.pop(key, None)

        task = asyncio.create_task(self._run(record, run_fn))
        self._asyncio_tasks[record.task_id] = task
        logger.info("execution_submitted task_id=%s employee=%s", record.task_id, employee_name)
        return record

    async def _run(self, record: ExecutionRecord, run_fn) -> None:
        record.status = ExecutionStatus.RUNNING
        record.started_at = time.time()
        try:
            await run_fn(record)
        except asyncio.CancelledError:
            record.status = ExecutionStatus.CANCELLED
            record.error = "Task cancelled"
            record.completed_at = time.time()
            logger.info("execution_cancelled task_id=%s", record.task_id)
        except Exception as e:
            record.status = ExecutionStatus.FAILED
            record.error = str(e)
            record.completed_at = time.time()
            logger.exception("execution_failed task_id=%s error=%s", record.task_id, e)
        finally:
            self._asyncio_tasks.pop(record.task_id, None)

    def get(self, task_id: str) -> Optional[ExecutionRecord]:
        return self._tasks.get(task_id)

    def list(self, limit: int = 50, status: Optional[str] = None) -> List[ExecutionRecord]:
        records = list(self._tasks.values())
        if status:
            try:
                st = ExecutionStatus(status)
                records = [r for r in records if r.status == st]
            except ValueError:
                pass
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    async def cancel(self, task_id: str) -> bool:
        """Cancel a queued/running execution."""
        record = self._tasks.get(task_id)
        if not record:
            return False
        task = self._asyncio_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        elif record.status == ExecutionStatus.QUEUED:
            record.status = ExecutionStatus.CANCELLED
            record.completed_at = time.time()
        return True


# 全局单例
_execution_queue: Optional[ExecutionQueue] = None


def get_execution_queue() -> ExecutionQueue:
    """Get the global execution queue singleton."""
    global _execution_queue
    if _execution_queue is None:
        _execution_queue = ExecutionQueue()
        logger.info("execution_queue_singleton_created")
    return _execution_queue
