"""Configuration for the Brain connector.

All values come from the environment (prefix ``CONNECTOR_BRAIN_``); no secrets live here —
supplier credentials are resolved from Vault via ``credentials_ref`` at auth time.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNECTOR_BRAIN_")

    base_url: str = "http://api.brain.com.ua"
    """Brain API base URL (see brain_api_documentation.md)."""

    requests_per_second: float = 3.0
    """Documented Brain limit: max 3 req/s per account."""

    session_ttl_seconds: float = 1800.0
    """How long a SID is reused before re-authenticating."""

    page_size: int = 1000
    """products/ page size (OWN_MODE max is 1000)."""

    request_timeout_seconds: float = 30.0

    otlp_endpoint: str | None = None
    env: str = "dev"

    # Brain error codes that mean "session expired" -> invalidate SID and retry once.
    # Confirm against Brain's error table before production; overridable via env.
    session_expired_codes: frozenset[int] = frozenset({102, 103})

    rate_limit_error_code: int = 115
    """Brain error code returned on 429 Too Many Requests."""
