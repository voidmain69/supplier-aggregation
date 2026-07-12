"""Sync-orchestrator configuration (env prefix ``SYNC_ORCHESTRATOR_``).

The account schedule is config (``SYNC_ORCHESTRATOR_ACCOUNTS`` as JSON): which accounts to
sync and how often. No secrets here — only ``credentials_ref`` (a Vault pointer).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sync_orchestrator.domain.schedule import AccountSchedule


class AccountConfig(BaseModel):
    """One scheduled account (a supplier can have several with different terms)."""

    account_id: str = Field(description="Account ULID to sync.")
    supplier_code: str = Field(
        description="Supplier the connector is registered under, e.g. brain."
    )
    credentials_ref: str | None = Field(default=None, description="Vault path (a pointer).")
    settlement_currency: str = Field(description="ISO-4217 code the account settles in.")
    kind: str = Field(default="all", description="products | offers | all.")
    interval_seconds: float = Field(default=3600.0, description="Minimum seconds between syncs.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNC_ORCHESTRATOR_")

    db_dsn: str = "postgresql+asyncpg://sa:sa_dev_only@localhost:5432/sa"
    kafka_bootstrap: str = "localhost:19092"
    poll_interval_seconds: float = 60.0
    accounts: list[AccountConfig] = Field(default_factory=list)

    otlp_endpoint: str | None = None
    env: str = "dev"

    def schedules(self) -> list[AccountSchedule]:
        """The configured accounts as domain schedules."""
        return [
            AccountSchedule(
                account_id=a.account_id,
                supplier_code=a.supplier_code,
                credentials_ref=a.credentials_ref,
                settlement_currency=a.settlement_currency,
                kind=a.kind,
                interval_seconds=a.interval_seconds,
            )
            for a in self.accounts
        ]
