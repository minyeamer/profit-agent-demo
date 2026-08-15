import pytest

from profit_agent_demo.config import OPENAI_API_BASE_URL, NVIDIA_API_BASE_URL, load_settings


def _set_database_environment(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.example")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "analytics")
    monkeypatch.setenv("PGUSER", "readonly")
    monkeypatch.setenv("PGPASSWORD", "not-a-real-secret")


def test_load_settings_uses_common_openai_variables(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.setenv("API_TYPE", "openai")
    monkeypatch.setenv("API_KEY", "not-a-real-api-key")
    monkeypatch.setenv("MODEL", "gpt-4o-mini")

    settings = load_settings()

    assert settings.api_type == "openai"
    assert settings.api_key == "not-a-real-api-key"
    assert settings.model == "gpt-4o-mini"
    assert settings.api_base_url == OPENAI_API_BASE_URL
    assert "not-a-real-secret" not in repr(settings)
    assert "not-a-real-api-key" not in repr(settings)


def test_nvidia_uses_default_endpoint_and_rate_limit(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.setenv("API_TYPE", "nvidia")
    monkeypatch.setenv("API_KEY", "not-a-real-api-key")
    monkeypatch.setenv("MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

    settings = load_settings()

    assert settings.api_type == "nvidia"
    assert settings.api_base_url == NVIDIA_API_BASE_URL
    assert settings.requests_per_minute == 40


def test_api_base_url_can_override_provider_default(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.setenv("API_TYPE", "nvidia")
    monkeypatch.setenv("API_KEY", "not-a-real-api-key")
    monkeypatch.setenv("API_BASE_URL", "https://example.test/v1")

    settings = load_settings()

    assert settings.api_base_url == "https://example.test/v1"


def test_unknown_api_type_is_rejected(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.setenv("API_TYPE", "other")
    monkeypatch.setenv("API_KEY", "not-a-real-api-key")

    with pytest.raises(ValueError, match="API_TYPE"):
        load_settings()


def test_data_tools_can_skip_api_key_validation(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_TYPE", raising=False)

    settings = load_settings(require_api_key=False)

    assert settings.api_key is None
    assert settings.api_type == "openai"


def test_api_key_is_required_for_chat_requests(monkeypatch):
    _set_database_environment(monkeypatch)
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(ValueError, match="API_KEY"):
        load_settings()
