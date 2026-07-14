"""MCP gateway configuration (env prefix ``MCP_GATEWAY_``)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_GATEWAY_")

    catalog_base_url: str = "http://localhost:8081"
    offer_base_url: str = "http://localhost:8082"
    price_history_base_url: str = "http://localhost:8083"
    search_base_url: str = "http://localhost:8086"
    request_timeout_seconds: float = 10.0

    otlp_endpoint: str | None = None
    env: str = "dev"
