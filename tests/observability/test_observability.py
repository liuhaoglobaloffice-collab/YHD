from src.observability.metrics import MetricsCollector
from src.observability.tracing import TracingContext
from src.observability.alerts import AlertManager


def test_observability_metrics_and_alert_flow():
    collector = MetricsCollector()
    collector.record_metric("api_latency", 10)
    collector.record_metric("task_execution_time", 5)
    collector.record_metric("workflow_success_rate", 1)
    collector.record_metric("error_count", 0)

    trace = TracingContext()
    trace.record_request("req-1")
    trace.record_agent("agent-1")
    trace.record_workflow("wf-1")
    trace.record_llm("provider-openai")
    trace.record_result("ok")

    alert = AlertManager()
    alert.record_error_threshold(5)
    alert.record_resource_threshold(90)
    alert.record_cost_threshold(100)

    assert alert.evaluate({"error_count": 2, "resource": 50, "cost": 90}) == []
    assert alert.evaluate({"error_count": 7, "resource": 50, "cost": 90})
