from enum import Enum


class Permission(str, Enum):
    KNOWLEDGE_READ = "knowledge.read"
    KNOWLEDGE_WRITE = "knowledge.write"
    TASK_EXECUTE = "task.execute"
    WORKFLOW_APPROVE = "workflow.approve"
    AUDIT_EXPORT = "audit.export"

    @classmethod
    def values(cls):
        return [p.value for p in cls]
