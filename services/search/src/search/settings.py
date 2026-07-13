"""Search configuration (env prefix ``SEARCH_``). No secrets here."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEARCH_")

    db_dsn: str = "postgresql+asyncpg://sa:sa_dev_only@localhost:5432/sa"
    kafka_bootstrap: str = "localhost:19092"
    consumer_group: str = "search.index"

    otlp_endpoint: str | None = None
    env: str = "dev"
