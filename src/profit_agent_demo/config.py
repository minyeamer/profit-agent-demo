import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    pg_schema: str
    profit_daily_function: str
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str
    agent_backend: str
    hermes_command: str
    hermes_max_turns: int
    streamlit_port: int
    streamlit_bind_address: str

    def __repr__(self) -> str:
        return (
            f"Settings(pg_host={self.pg_host!r}, pg_port={self.pg_port}, "
            f"pg_database={self.pg_database!r}, pg_user={self.pg_user!r}, "
            "pg_password='<redacted>', "
            f"pg_schema={self.pg_schema!r}, profit_daily_function={self.profit_daily_function!r}, "
            f"openai_model={self.openai_model!r}, streamlit_port={self.streamlit_port}, "
            f"streamlit_bind_address={self.streamlit_bind_address!r})"
        )


def _secret_value(name: str) -> str | None:
    try:
        from streamlit import secrets

        value = secrets.get(name)
    except Exception:
        return None
    return str(value) if value is not None and value != "" else None


def _value(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or _secret_value(name) or default


def _required(name: str) -> str:
    value = _value(name)
    if not value:
        raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {name}")
    return value


def load_settings() -> Settings:
    return Settings(
        pg_host=_required("PGHOST"),
        pg_port=int(_value("PGPORT") or "5432"),
        pg_database=_required("PGDATABASE"),
        pg_user=_required("PGUSER"),
        pg_password=_required("PGPASSWORD"),
        pg_schema=_value("PGSCHEMA") or "analytics",
        profit_daily_function=_value("PROFIT_DAILY_FUNCTION") or "analytics.profit_daily",
        openai_api_key=_value("OPENAI_API_KEY"),
        openai_base_url=_value("OPENAI_BASE_URL"),
        openai_model=_value("OPENAI_MODEL") or "gpt-4o-mini",
        agent_backend=_value("AGENT_BACKEND") or "auto",
        hermes_command=_value("HERMES_COMMAND") or "hermes",
        hermes_max_turns=int(_value("HERMES_MAX_TURNS") or "12"),
        streamlit_port=int(_value("STREAMLIT_PORT") or "8510"),
        streamlit_bind_address=_value("STREAMLIT_BIND_ADDRESS") or "127.0.0.1",
    )
