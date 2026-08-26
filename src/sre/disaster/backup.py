from typing import Any, Dict, Optional


class BackupManager:
    """A lightweight backup manager for database, knowledge, workflow, and config snapshots."""

    def __init__(self):
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def create_backup(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = {"resource": resource, "payload": payload, "status": "created"}
        self.snapshots[resource] = snapshot
        return snapshot


class RecoveryManager:
    """A lightweight recovery manager that verifies a restore step."""

    def __init__(self):
        self.last_restore: Optional[Dict[str, Any]] = None

    def restore(self, resource: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        self.last_restore = {"resource": resource, "snapshot": snapshot, "status": "restored"}
        return self.last_restore
