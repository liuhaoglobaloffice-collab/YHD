from typing import Dict, List, Optional


class TracingContext:
    """Simple request-to-agent-to-workflow-to-LLM trace aggregator."""

    def __init__(self):
        self.trace: List[str] = []

    def record_request(self, request_id: str) -> None:
        self.trace.append(f"request:{request_id}")

    def record_agent(self, agent_id: str) -> None:
        self.trace.append(f"agent:{agent_id}")

    def record_workflow(self, workflow_id: str) -> None:
        self.trace.append(f"workflow:{workflow_id}")

    def record_llm(self, provider: str) -> None:
        self.trace.append(f"llm:{provider}")

    def record_result(self, result: str) -> None:
        self.trace.append(f"result:{result}")

    def as_dict(self) -> Dict[str, List[str]]:
        return {"trace": list(self.trace)}
