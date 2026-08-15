import os
from dataclasses import dataclass


OPENAI_API_BASE_URL = "https://api.openai.com/v1"
NVIDIA_API_BASE_URL = "https://integrate.api.nvidia.com/v1"


@dataclass(frozen=True)
class ProviderSpec:
    default_base_url: str
    default_model: str
    requests_per_minute: int | None


PROVIDERS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        default_base_url=OPENAI_API_BASE_URL,
        default_model="gpt-4o-mini",
        requests_per_minute=None,
    ),
    "nvidia": ProviderSpec(
        default_base_url=NVIDIA_API_BASE_URL,
        default_model="nvidia/nemotron-3-ultra-550b-a55b",
        requests_per_minute=40,
    ),
}


@dataclass(frozen=True)
class Settings:
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    pg_schema: str
    profit_daily_function: str
    api_type: str
    api_key: str | None
    api_base_url: str
    model: str
    requests_per_minute: int | None
    streamlit_port: int
    streamlit_bind_address: str

    def __repr__(self) -> str:
        return (
            f"Settings(pg_host={self.pg_host!r}, pg_port={self.pg_port}, "
            f"pg_database={self.pg_database!r}, pg_user={self.pg_user!r}, "
            "pg_password='<redacted>', api_key='<redacted>', "
            f"pg_schema={self.pg_schema!r}, api_type={self.api_type!r}, "
            f"model={self.model!r}, streamlit_port={self.streamlit_port}, "
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


def _provider_spec(api_type: str) -> ProviderSpec:
    try:
        return PROVIDERS[api_type]
    except KeyError as exc:
        supported = ", ".join(PROVIDERS)
        raise ValueError(f"API_TYPE은 다음 중 하나여야 합니다: {supported}") from exc


def load_settings(*, require_api_key: bool = True) -> Settings:
    api_type = (_value("API_TYPE") or "openai").lower()
    provider = _provider_spec(api_type)
    api_base_url = _value("API_BASE_URL") or provider.default_base_url
    return Settings(
        pg_host=_required("PGHOST"),
        pg_port=int(_value("PGPORT") or "5432"),
        pg_database=_required("PGDATABASE"),
        pg_user=_required("PGUSER"),
        pg_password=_required("PGPASSWORD"),
        pg_schema=_value("PGSCHEMA") or "analytics",
        profit_daily_function=_value("PROFIT_DAILY_FUNCTION") or "analytics.profit_daily",
        api_type=api_type,
        api_key=_required("API_KEY") if require_api_key else _value("API_KEY"),
        api_base_url=api_base_url,
        model=_value("MODEL") or provider.default_model,
        requests_per_minute=provider.requests_per_minute,
        streamlit_port=int(_value("STREAMLIT_PORT") or "8510"),
        streamlit_bind_address=_value("STREAMLIT_BIND_ADDRESS") or "127.0.0.1",
    )
