"""Sync monitoring API: account status + manual trigger (SQLite)."""

from __future__ import annotations

import httpx
import pytest
from sa_persistence.outbox import OutboxRow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sync_orchestrator.api.deps import get_session_factory, get_settings
from sync_orchestrator.main import create_app
from sync_orchestrator.settings import AccountConfig, Settings

SessionFactory = async_sessionmaker[AsyncSession]
_ACCT = "01J0000000000000000ACCT1"


def _settings() -> Settings:
    return Settings(
        accounts=[
            AccountConfig(
                account_id=_ACCT,
                supplier_code="brain",
                settlement_currency="USD",
                kind="all",
                interval_seconds=3600.0,
                mode="delta",
            )
        ]
    )


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    app.dependency_overrides[get_settings] = _settings
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_accounts__lists_status_without_leaking_financial_terms(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        body = (await client.get("/v1/sync/accounts")).json()

    assert len(body) == 1
    account = body[0]
    assert account["account_id"] == _ACCT
    assert account["supplier_code"] == "brain"
    assert account["status"] == "never"
    assert account["last_requested_at"] is None
    # hard rule 6: never expose credentials or financial terms
    assert "settlement_currency" not in account
    assert "credentials_ref" not in account


async def test_trigger__emits_event_and_marks_requested(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    async with client:
        resp = await client.post(f"/v1/sync/accounts/{_ACCT}/trigger")
        assert resp.status_code == 200
        assert resp.json()["account_id"] == _ACCT
        after = (await client.get("/v1/sync/accounts")).json()[0]

    assert after["status"] == "ok"
    assert after["last_requested_at"] is not None

    async with sqlite_session_factory() as session:
        outbox = (await session.execute(select(OutboxRow))).scalars().all()
    assert len(outbox) == 1
    assert outbox[0].topic == "sa.sync.job"
    assert outbox[0].payload["type"] == "sync.job.requested"
    assert outbox[0].payload["subject"] == _ACCT


async def test_trigger__unknown_account_is_404(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/sync/accounts/01JUNKNOWNACCOUNT00000000/trigger")
    assert resp.status_code == 404
