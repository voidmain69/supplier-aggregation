"""Drive a full account sync through the connector into the outbox.

Fetches from the supplier (categories -> products, and offers) and hands the normalized
DTOs to the idempotent ``sync_products`` / ``sync_offers`` staging functions. ``kind`` selects
what to sync. Re-running is safe: unchanged products/prices stage no new events.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from connector_brain.connector import BrainConnector
from connector_brain.sync import sync_offers, sync_products
from sa_connector_sdk.dto import AccountCtx


async def run_account_sync(
    connector: BrainConnector,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    supplier_code: str,
    account: AccountCtx,
    sync_job_id: str,
    kind: str,
) -> None:
    """Sync the account per ``kind`` (products | offers | all)."""
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
