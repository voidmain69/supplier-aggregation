"""Handle ``sync.job.requested``: build the account's connector and run a full sync.

The orchestrator schedules; this consumer does the fetching. ``connector_factory`` is
injected (the connector needs the account's credentials, resolved from Vault in production),
so the handler is unit-testable against a faked Brain. The sync itself is idempotent, so
at-least-once redelivery is safe.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sa_messaging import EventHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from connector_brain.connector import BrainConnector
from connector_brain.full_sync import run_account_sync
from sa_connector_sdk.dto import AccountCtx
from sa_contracts.events.sync_job_requested import SyncJobRequested

ConnectorFactory = Callable[[AccountCtx], BrainConnector]


def build_sync_handler(
    session_factory: async_sessionmaker[AsyncSession],
    connector_factory: ConnectorFactory,
) -> EventHandler:
    """Build the ``sync.job.requested`` handler bound to a session factory + connector factory."""

    async def handle(envelope: dict[str, Any]) -> None:
        request = SyncJobRequested(**envelope["data"])
        account = AccountCtx(
            account_id=request.account_id,
            supplier_code=request.supplier_code,
            credentials_ref=request.credentials_ref or "",
            settlement_currency=request.settlement_currency,
        )
        connector = connector_factory(account)
        await run_account_sync(
            connector,
            session_factory,
            supplier_code=request.supplier_code,
            account=account,
            sync_job_id=request.sync_job_id,
            kind=request.kind.value,
            mode=request.mode.value if request.mode is not None else "full",
        )

    return handle
