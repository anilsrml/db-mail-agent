from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tüm servislerin ortam değişkenlerinden okuduğu ortak ayarlar."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:exacto"
    openrouter_reasoning_effort: str = "low"
    llm_dry_run: bool = True

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_dry_run: bool = True

    postgres_dsn: str = (
        "postgresql://stock_reader:change-me-reader@postgres:5432/stock_demo"
    )
    mcp_server_url: str = "http://mcp-server:8003/mcp"
    db_agent_url: str = "http://db-agent:8001"
    telegram_agent_url: str = "http://telegram-agent:8002"
    http_timeout_seconds: float = 30.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

