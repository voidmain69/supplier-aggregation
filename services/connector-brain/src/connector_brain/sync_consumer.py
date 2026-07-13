"""Sync consumer: run a full account sync when the orchestrator requests one.

Consumes ``sync.job.requested`` (from sync-orchestrator) and drives the Brain connector to
fetch + stage discovered/price-changed events. Run with ``python -m connector_brain.sync_consumer``.

Raw responses are archived to S3/MinIO before normalization (hard rule 9). Production still
needs a Vault-backed ``CredentialResolver`` (credentials_ref -> login/password); wire it in
:func:`_credential_resolver`.
"""

from __future__ import annotations

import asyncio

import httpx
from sa_messaging import KafkaEventConsumer
from sa_persistence.db import create_engine, create_session_factory

from connector_brain.adapters.brain_client import BrainClient, CredentialResolver
from connector_brain.adapters.s3_archive import S3RawArchive, build_s3_client
from connector_brain.connector import BrainConnector
from connector_brain.events.sync_handler import ConnectorFactory, build_sync_handler
from connector_brain.settings import Settings
from sa_connector_sdk.dto import AccountCtx
from sa_connector_sdk.raw_archive import RawArchive
from sa_contracts import EVENT_REGISTRY

_SYNC_REQUESTED = "sync.job.requested"


def build_connector_factory(
    settings: Settings,
    http: httpx.AsyncClient,
    credentials: CredentialResolver,
    archive: RawArchive,
) -> ConnectorFactory:
    """Return a factory that builds a per-account BrainConnector sharing one HTTP client."""

    def _make(account: AccountCtx) -> BrainConnector:
        client = BrainClient(
            settings=settings, http=http, credentials=credentials, archive=archive, account=account
        )
        return BrainConnector(client=client, account=account, settings=settings)

    return _make


def _credential_resolver(settings: Settings) -> CredentialResolver:
    raise NotImplementedError(
        "connector-brain sync-consumer needs a Vault-backed CredentialResolver "
        "(credentials_ref -> login/password). Wire it here before running in production."
    )


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    credentials = _credential_resolver(settings)
    archive = S3RawArchive(client=build_s3_client(settings), bucket=settings.s3_bucket)
    await archive.ensure_bucket()
    async with httpx.AsyncClient(
        base_url=settings.base_url, timeout=settings.request_timeout_seconds
    ) as http:
        factory = build_connector_factory(settings, http, credentials, archive)
        consumer = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=settings.sync_consumer_group,
            topics=[EVENT_REGISTRY[_SYNC_REQUESTED].topic],
        )
        async with consumer:
            await consumer.consume(build_sync_handler(session_factory, factory))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
