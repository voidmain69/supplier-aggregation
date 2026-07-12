"""Configuration for the Brain connector.

All values come from the environment (prefix ``CONNECTOR_BRAIN_``); no secrets live here —
supplier credentials are resolved from Vault via ``credentials_ref`` at auth time.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNECTOR_BRAIN_")

    db_dsn: str = "postgresql+asyncpg://sa:sa_dev_only@localhost:5432/sa"
    """Connector-owned store: supplier product identities, offer state and the outbox."""

    kafka_bootstrap: str = "localhost:19092"
    """Broker the outbox relay publishes discovered/price-changed events to."""

    sync_consumer_group: str = "connector-brain.sync"
    """Consumer group for sync.job.requested (the sync-orchestrator's schedule trigger)."""

    base_url: str = "http://api.brain.com.ua"
    """Brain API base URL (see brain_api_documentation.md)."""

    requests_per_second: float = 3.0
    """Documented Brain limit: max 3 req/s per account."""

    session_ttl_seconds: float = 1800.0
    """How long a SID is reused before re-authenticating."""

    page_size: int = 1000
    """products/ page size (OWN_MODE max is 1000)."""

    request_timeout_seconds: float = 30.0

    # Raw archive (S3/MinIO): every Brain response is stored before normalization (hard rule 9).
    # These are infra secrets injected from the environment, not supplier credentials.
    s3_endpoint_url: str | None = "http://localhost:9000"
    """S3 endpoint; set for MinIO/S3-compatible stores, leave unset (None) for real AWS S3."""

    s3_bucket: str = "sa-raw"
    """Bucket that holds raw supplier payloads (lifecycle-managed, see infrastructure standard)."""

    s3_access_key: str = "sa"
    s3_secret_key: str = "sa_dev_only"  # noqa: S105 -- dev MinIO default, overridden by env in prod
    s3_region: str = "us-east-1"

    # Supplier credentials: resolved from Vault at auth time via credentials_ref (hard rule 6).
    # Leave vault_addr unset to fall back to dev_login/dev_password (local runs, one test account).
    vault_addr: str | None = None
    """Vault server URL. When set, the sync-consumer resolves supplier creds from Vault."""

    vault_token: str | None = None
    """Vault token (dev/CI); in k8s it is injected by external-secrets, never committed."""

    vault_kv_mount: str = "secret"
    """KV v2 mount that holds ``suppliers/<supplier>/<account>`` secrets."""

    dev_login: str | None = None
    """Dev fallback login (no Vault); use only against a test supplier account."""

    dev_password: str | None = None
    """Dev fallback password; pairs with dev_login when Vault is not configured."""

    otlp_endpoint: str | None = None
    env: str = "dev"

    # Brain error codes that mean "session expired" -> invalidate SID and retry once.
    # Confirm against Brain's error table before production; overridable via env.
    session_expired_codes: frozenset[int] = frozenset({102, 103})

    rate_limit_error_code: int = 115
    """Brain error code returned on 429 Too Many Requests."""
