"""Search configuration (env prefix ``SEARCH_``). No secrets here."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEARCH_")

    db_dsn: str = "postgresql+asyncpg://sa:sa_dev_only@localhost:5432/sa"
    kafka_bootstrap: str = "localhost:19092"
    consumer_group: str = "search.index"

    # Base URL of a Text-Embeddings-Inference server (bge-m3). Unset => offline HashingEmbedder.
    embedder_url: str | None = None

    otlp_endpoint: str | None = None
    env: str = "dev"
