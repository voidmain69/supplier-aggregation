"""Delta vs full account sync + watermark handling."""

from __future__ import annotations

from datetime import UTC, datetime

from connector_brain.adapters.watermark_repo import get_watermark, set_watermark
from connector_brain.full_sync import run_account_sync
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_connector_sdk.dto import AccountCtx

SessionFactory = async_sessionmaker[AsyncSession]

ACCOUNT = AccountCtx(
    account_id="acc1",
    supplier_code="brain",
    credentials_ref="suppliers/brain/acc1",
    settlement_currency="USD",
)
_SINCE = datetime(2026, 7, 12, 9, 0, tzinfo=UTC)


async def _run(factory: SessionFactory, connector: object, *, mode: str) -> int:
    await run_account_sync(
        connector,  # type: ignore[arg-type]
        factory,
        supplier_code="brain",
        account=ACCOUNT,
        sync_job_id="01JSYNC",
        kind="all",
        mode=mode,
    )
    publisher = InMemoryPublisher()
    return await OutboxRelay(factory, publisher).drain()


async def test_delta__with_watermark__fetches_modified_and_advances_watermark(
    sqlite_session_factory: SessionFactory, build_connector
) -> None:
    connector, _ = build_connector(page_size=100)
    async with sqlite_session_factory() as session, session.begin():
        await set_watermark(session, supplier_code="brain", account_id="acc1", synced_at=_SINCE)

    published = await _run(sqlite_session_factory, connector, mode="delta")

    assert published >= 1  # the modified product(s) staged discovered/price events
    async with sqlite_session_factory() as session:
        watermark = await get_watermark(session, supplier_code="brain", account_id="acc1")
    assert watermark is not None and watermark > _SINCE  # advanced to the sync start time


async def test_delta__without_watermark__falls_back_to_full(
    sqlite_session_factory: SessionFactory, build_connector
) -> None:
    connector, _ = build_connector(page_size=100)

    published = await _run(sqlite_session_factory, connector, mode="delta")

    assert published >= 1  # full catalog walk still staged events
    async with sqlite_session_factory() as session:
        watermark = await get_watermark(session, supplier_code="brain", account_id="acc1")
    assert watermark is not None  # first sync sets the baseline for subsequent deltas


async def test_full__sets_watermark(
    sqlite_session_factory: SessionFactory, build_connector
) -> None:
    connector, _ = build_connector(page_size=100)

    await _run(sqlite_session_factory, connector, mode="full")

    async with sqlite_session_factory() as session:
        assert await get_watermark(session, supplier_code="brain", account_id="acc1") is not None
