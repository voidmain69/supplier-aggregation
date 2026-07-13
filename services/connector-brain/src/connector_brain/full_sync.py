"""Drive an account sync through the connector into the outbox.

Two modes:
- **full** walks the whole catalog (categories -> products) and all offers.
- **delta** fetches only what the supplier reports changed since the account's watermark
  (``modified_products``), then re-stages those products/offers. The first sync of an account
  has no watermark, so delta transparently falls back to full.

Either way the normalized DTOs go through the idempotent ``sync_products`` / ``sync_offers``
staging functions, and the watermark is advanced to the moment the sync started (so a change
made mid-sync is re-caught next time rather than missed). ``kind`` selects products/offers/both.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from connector_brain.adapters.watermark_repo import get_watermark, set_watermark
from connector_brain.connector import BrainConnector
from connector_brain.sync import sync_offers, sync_products
from sa_connector_sdk.dto import AccountCtx, RawOffer, RawProduct
from sa_core.time import utc_now


async def run_account_sync(
    connector: BrainConnector,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    supplier_code: str,
    account: AccountCtx,
    sync_job_id: str,
    kind: str,
    mode: str = "full",
) -> None:
    """Sync the account per ``kind`` (products | offers | all) and ``mode`` (full | delta)."""
    started_at = utc_now()
    since: datetime | None = None
    if mode == "delta":
        async with session_factory() as session:
            since = await get_watermark(
                session, supplier_code=supplier_code, account_id=account.account_id
            )

    if since is not None:
        await _sync_delta(
            connector,
            session_factory,
            supplier_code=supplier_code,
            account=account,
            sync_job_id=sync_job_id,
            kind=kind,
            since=since,
        )
    else:
        await _sync_full(
            connector,
            session_factory,
            supplier_code=supplier_code,
            account=account,
            sync_job_id=sync_job_id,
            kind=kind,
        )

    async with session_factory() as session, session.begin():
        await set_watermark(
            session,
            supplier_code=supplier_code,
            account_id=account.account_id,
            synced_at=started_at,
        )


async def _sync_full(
    connector: BrainConnector,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    supplier_code: str,
    account: AccountCtx,
    sync_job_id: str,
    kind: str,
) -> None:
    if kind in ("products", "all"):
        async for category in connector.fetch_categories():
            cursor: str | None = None
            while True:
                page = await connector.fetch_products(category.external_id, cursor)
                await sync_products(
                    session_factory,
                    page.items,
                    supplier_code=supplier_code,
                    sync_job_id=sync_job_id,
                )
                if page.next_cursor is None:
                    break
                cursor = page.next_cursor

    if kind in ("offers", "all"):
        offers = [offer async for offer in connector.fetch_offers(account)]
        await sync_offers(
            session_factory,
            offers,
            supplier_code=supplier_code,
            account=account,
            sync_job_id=sync_job_id,
        )


async def _sync_delta(
    connector: BrainConnector,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    supplier_code: str,
    account: AccountCtx,
    sync_job_id: str,
    kind: str,
    since: datetime,
) -> None:
    products: list[RawProduct] = []
    offers: list[RawOffer] = []
    async for delta in connector.fetch_deltas(since):
        product, offer = await connector.fetch_delta_item(delta.external_id, account)
        products.append(product)
        if offer is not None:
            offers.append(offer)

    # Products first: sync_offers skips an offer whose product is not yet discovered.
    if kind in ("products", "all"):
        await sync_products(
            session_factory, products, supplier_code=supplier_code, sync_job_id=sync_job_id
        )
    if kind in ("offers", "all"):
        await sync_offers(
            session_factory,
            offers,
            supplier_code=supplier_code,
            account=account,
            sync_job_id=sync_job_id,
        )
