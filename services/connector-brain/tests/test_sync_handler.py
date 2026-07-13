"""sync.job.requested handler: build the connector and run a full sync into the outbox."""

from __future__ import annotations

from typing import Any

from connector_brain.events.sync_handler import build_sync_handler
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts import EVENT_REGISTRY
from sa_core.events import make_cloud_event

SessionFactory = async_sessionmaker[AsyncSession]


def _event(*, kind: str, mode: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "supplier_code": "brain",
        "account_id": "acc1",
        "credentials_ref": "vault/brain/acc1",
        "settlement_currency": "USD",
        "kind": kind,
        "sync_job_id": "01J0000000000000000SYNC1",
        "requested_at": "2026-07-12T12:00:00Z",
    }
    if mode is not None:
        data["mode"] = mode
    return make_cloud_event(
        type="sync.job.requested",
        source="//sa/sync-orchestrator",
        subject="acc1",
        dataschema=EVENT_REGISTRY["sync.job.requested"].dataschema,
        data=data,
    )


async def _published_topics(factory: SessionFactory) -> set[str]:
    publisher = InMemoryPublisher()
    await OutboxRelay(factory, publisher).drain()
    return {topic for topic, _key, _payload in publisher.published}


async def test_sync_handler__all_emits_discovered_and_price_changed(
    sqlite_session_factory: SessionFactory, build_connector: Any
) -> None:
    connector, _ = build_connector(page_size=10)
    handler = build_sync_handler(sqlite_session_factory, lambda _account: connector)

    await handler(_event(kind="all"))

    topics = await _published_topics(sqlite_session_factory)
    assert "sa.supplier.product" in topics  # discovered
    assert "sa.supplier.offer" in topics  # price-changed (product was discovered first)


async def test_sync_handler__products_only_emits_no_offers(
    sqlite_session_factory: SessionFactory, build_connector: Any
) -> None:
    connector, _ = build_connector(page_size=10)
    handler = build_sync_handler(sqlite_session_factory, lambda _account: connector)

    await handler(_event(kind="products"))

    topics = await _published_topics(sqlite_session_factory)
    assert topics == {"sa.supplier.product"}


async def test_sync_handler__rerun_is_idempotent(
    sqlite_session_factory: SessionFactory, build_connector: Any
) -> None:
    connector, _ = build_connector(page_size=10)
    handler = build_sync_handler(sqlite_session_factory, lambda _account: connector)

    await handler(_event(kind="all"))
    first = await _drain_count(sqlite_session_factory)
    await handler(_event(kind="all"))  # nothing changed -> no new events
    assert await _drain_count(sqlite_session_factory) == 0
    assert first > 0


async def test_sync_handler__delta_mode_runs_delta_path(
    sqlite_session_factory: SessionFactory, build_connector: Any
) -> None:
    from datetime import UTC, datetime  # noqa: PLC0415

    from connector_brain.adapters.watermark_repo import set_watermark  # noqa: PLC0415

    connector, _ = build_connector(page_size=10)
    async with sqlite_session_factory() as session, session.begin():
        await set_watermark(
            session,
            supplier_code="brain",
            account_id="acc1",
            synced_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
    handler = build_sync_handler(sqlite_session_factory, lambda _account: connector)

    await handler(_event(kind="all", mode="delta"))

    topics = await _published_topics(sqlite_session_factory)
    assert "sa.supplier.product" in topics  # delta fetched the modified product(s)


async def _drain_count(factory: SessionFactory) -> int:
    return await OutboxRelay(factory, InMemoryPublisher()).drain()
