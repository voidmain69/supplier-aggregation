"""Product sync: turn fetched RawProducts into discovered events via the outbox.

Each product is processed in its own transaction: identity resolution + change detection +
(if new) enqueuing the ``supplier.product.discovered`` event commit together, so an event
is never emitted without its identity and vice versa. Re-running a sync is idempotent —
already-known products produce no new events.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from connector_brain.adapters.identity_repo import resolve_and_stage
from connector_brain.events.mapping import product_discovered_record
from sa_connector_sdk.dto import RawProduct
from sa_connector_sdk.normalize import content_hash


@dataclass
class SyncStats:
    discovered: int = 0
    changed: int = 0
    unchanged: int = 0


async def sync_products(
    session_factory: async_sessionmaker[AsyncSession],
    products: Iterable[RawProduct],
    *,
    supplier_code: str,
    sync_job_id: str,
) -> SyncStats:
    """Process products, staging discovered events for first-seen ones. Returns counts."""
    stats = SyncStats()
    for product in products:
        fingerprint = content_hash(product.content_fields())
        async with session_factory() as session, session.begin():
            supplier_product_id, state = await resolve_and_stage(
                session,
                supplier_code=supplier_code,
                external_id=product.external_id,
                content_hash=fingerprint,
            )
            if state == "new":
                enqueue(
                    session,
                    product_discovered_record(
                        product,
                        supplier_product_id=supplier_product_id,
                        supplier_code=supplier_code,
                        sync_job_id=sync_job_id,
                    ),
                )
                stats.discovered += 1
            elif state == "changed":
                stats.changed += 1
            else:
                stats.unchanged += 1
    return stats
