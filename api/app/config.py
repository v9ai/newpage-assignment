from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration.

    Values load from the environment, with file fallbacks: `.env` holds
    defaults, `.env.local` holds secrets/overrides and wins over `.env`.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DocChat"
    version: str = "0.1.0"

    openai_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-5-mini"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384

    database_url: str = "postgresql+psycopg://docchat:docchat@localhost:5432/docchat"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "docchat_chunks"

    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_api_key(settings: Settings) -> None:
    """Fail fast at startup when the OpenAI key is absent.

    Raises RuntimeError with a setup hint instead of failing at first query.
    """
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env.local, "
            "add your key, and restart."
        )
