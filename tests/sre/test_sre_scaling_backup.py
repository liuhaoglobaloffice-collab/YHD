from src.sre.scaling.scaling import ScalingPolicy, ResourceMonitor, CapacityPlanner
from src.sre.disaster.backup import BackupManager, RecoveryManager


def test_scaling_and_backup_recovery_flow():
    monitor = ResourceMonitor()
    policy = ScalingPolicy()
    planner = CapacityPlanner(monitor, policy)

    monitor.samples = {"cpu": 85, "memory": 80, "queue": 50, "worker_load": 70, "llm_load": 40}
    action = planner.plan()
    assert action in {"scale_up", "scale_down", "scale_stable"}

    backup = BackupManager()
    snapshot = backup.create_backup("database", {"version": "v1"})
    assert snapshot["status"] == "created"

    recovery = RecoveryManager()
    restored = recovery.restore("database", snapshot)
    assert restored["status"] == "restored"
