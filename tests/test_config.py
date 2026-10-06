"""Unit tests for configuration loading."""

from src.core.config import Settings


def test_default_config_values():
    """Verify default configurations align with specification."""
    cfg = Settings()
    assert cfg.llm_base_url == "http://localhost:11434/v1"
    assert cfg.llm_model == "llama3.2:3b"
    assert cfg.llm_api_key == "ollama"
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8000


def test_custom_config_values():
    """Verify settings can be overridden."""
    cfg = Settings(
        llm_base_url="http://remote-ollama:11434/v1",
        llm_model="custom-model",
        llm_api_key="secret",
    )
    assert cfg.llm_base_url == "http://remote-ollama:11434/v1"
    assert cfg.llm_model == "custom-model"
    assert cfg.llm_api_key == "secret"
