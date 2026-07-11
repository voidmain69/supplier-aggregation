"""Catalog configuration (env prefix ``CATALOG_``). No secrets here."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CATALOG_")

    db_dsn: str = "postgresql+asyncpg://sa:sa_dev_only@localhost:5432/sa"
    kafka_bootstrap: str = "localhost:19092"
    consumer_group: str = "catalog.ingest"

    otlp_endpoint: str | None = None
    env: str = "dev"
