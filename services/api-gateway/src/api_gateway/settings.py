"""API-gateway configuration (env prefix ``API_GATEWAY_``).

No raw secrets live here: principals are keyed by the **SHA-256 hash** of their bearer
token (a hash is not a secret), so a dev config can be committed without leaking a usable
credential. In production the principal store is backed by Vault/DB instead (swap the
``PrincipalStore`` implementation).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PrincipalConfig(BaseModel):
    """A caller (service or AI agent) and the scopes its token grants."""

    subject: str = Field(description="Stable identity of the caller, e.g. `agent:pricing`.")
    scopes: list[str] = Field(default_factory=list, description="Scopes granted to this token.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_GATEWAY_")

    # Downstream service base URLs (the gateway reads over HTTP, never their DB).
    catalog_base_url: str = "http://localhost:8081"
    offer_base_url: str = "http://localhost:8082"
    price_history_base_url: str = "http://localhost:8083"
    matching_base_url: str = "http://localhost:8084"
    sync_orchestrator_base_url: str = "http://localhost:8085"
    request_timeout_seconds: float = 10.0

    # Auth: token SHA-256 hash -> principal. Load from env as JSON (API_GATEWAY_PRINCIPALS).
    principals: dict[str, PrincipalConfig] = Field(default_factory=dict)

    # Per-principal rate limit (token bucket).
    rate_limit_per_second: float = 20.0
    rate_limit_burst: int = 40

    # CORS allowlist for browser SPAs (e.g. curation-ui). Empty = no browser origin allowed.
    # Exact origins only (scheme+host+port), never "*": the gateway is credentialed.
    cors_allow_origins: list[str] = Field(
        default_factory=list,
        description="Exact browser origins allowed to call the gateway (e.g. the curation-ui URL).",
    )

    otlp_endpoint: str | None = None
    env: str = "dev"
