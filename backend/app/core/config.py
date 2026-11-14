"""Application settings loaded from environment variables and ``.env``."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Download Benchmark API"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://benchmark:benchmark@localhost:5432/download_benchmark"

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue: str = "download_tasks"
    rabbitmq_retry_queue: str = "download_tasks.retry"
    max_retries: int = 3
    retry_delay_ms: int = 2000

    http_timeout: float = 30.0
    default_requests: int = 10
    max_requests: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
