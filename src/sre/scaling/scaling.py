from dataclasses import dataclass
from typing import Dict, Iterable, Optional


class ScalingPolicy:
    """A small autoscaling policy that classifies pressure from a resource snapshot."""

    def __init__(self):
        self.thresholds = {
            "cpu": 80,
            "memory": 80,
            "queue": 40,
            "worker_load": 75,
            "llm_load": 60,
        }

    def decide(self, samples: Dict[str, float]) -> str:
        if samples.get("cpu", 0) >= self.thresholds["cpu"] or samples.get("queue", 0) >= self.thresholds["queue"]:
            return "scale_up"
        if samples.get("memory", 0) <= 20 and samples.get("worker_load", 0) <= 20:
            return "scale_down"
        return "scale_stable"


class ResourceMonitor:
    """Resource snapshot provider for deterministic SRE scaling decisions."""

    def __init__(self):
        self.samples: Dict[str, float] = {}

    def sample(self) -> Dict[str, float]:
        return dict(self.samples)


class CapacityPlanner:
    """Make a scale decision based on the monitor sample set."""

    def __init__(self, monitor: Optional[ResourceMonitor] = None, policy: Optional[ScalingPolicy] = None):
        self.monitor = monitor or ResourceMonitor()
        self.policy = policy or ScalingPolicy()

    def plan(self) -> str:
        return self.policy.decide(self.monitor.sample())
