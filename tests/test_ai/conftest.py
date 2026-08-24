"""
LiuHao AI OS Y1.0
Test fixtures for AI module tests
"""

import pytest

from src.security.secrets import SecretsManager


@pytest.fixture
def mock_secrets(monkeypatch):
    """Mock secrets manager with test API keys."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-moonshot-key")

    secrets = SecretsManager()
    secrets._keys = {
        "openai_api_key": "sk-test-openai-key",
        "anthropic_api_key": "sk-ant-test-key",
        "google_api_key": "test-google-key",
        "xai_api_key": "test-xai-key",
        "deepseek_api_key": "test-deepseek-key",
        "moonshot_api_key": "test-moonshot-key",
    }

    return secrets
