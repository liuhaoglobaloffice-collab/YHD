"""Metrics dashboard scaffolding for AI OS productization."""


class MetricDashboard:
    def __init__(self):
        self.metrics = {}

    def record(self, name, value):
        self.metrics[name] = value

    def snapshot(self):
        return dict(self.metrics)
