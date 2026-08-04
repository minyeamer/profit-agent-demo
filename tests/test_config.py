from profit_agent_demo.config import load_settings


def test_load_settings_uses_environment_variables(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.example")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "analytics")
    monkeypatch.setenv("PGUSER", "readonly")
    monkeypatch.setenv("PGPASSWORD", "not-a-real-secret")

    settings = load_settings()

    assert settings.pg_host == "db.example"
    assert settings.pg_port == 5432
    assert settings.pg_database == "analytics"
    assert settings.pg_password == "not-a-real-secret"
    assert "not-a-real-secret" not in repr(settings)


def test_settings_use_hermes_backend_when_no_llm_api_key_is_configured(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PGHOST", "db.example")
    monkeypatch.setenv("PGDATABASE", "analytics")
    monkeypatch.setenv("PGUSER", "readonly")
    monkeypatch.setenv("PGPASSWORD", "not-a-real-secret")

    settings = load_settings()

    assert settings.agent_backend == "auto"
    assert settings.hermes_command == "hermes"
    assert settings.hermes_max_turns == 12


def test_hermes_max_turns_can_be_configured(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.example")
    monkeypatch.setenv("PGDATABASE", "analytics")
    monkeypatch.setenv("PGUSER", "readonly")
    monkeypatch.setenv("PGPASSWORD", "not-a-real-secret")
    monkeypatch.setenv("HERMES_MAX_TURNS", "20")

    settings = load_settings()

    assert settings.hermes_max_turns == 20
