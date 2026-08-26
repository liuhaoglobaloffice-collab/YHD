"""Model configuration center scaffolding."""


class ModelCenter:
    def load_providers(self):
        return [
            {"provider": "OpenAI", "model": "gpt-4.1", "status": "ok"},
            {"provider": "Self Host", "model": "local-llm", "status": "ok"},
            {"provider": "Local LLM", "model": "local-llm", "status": "ok"},
        ]
