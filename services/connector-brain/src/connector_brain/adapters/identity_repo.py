"""Identity resolution + change detection for supplier products.

Mints a stable ``supplier_product_id`` on first sight and, on later syncs, reports whether
the product's content changed (by ``content_hash``). Runs inside the caller's transaction,
alongside the outbox enqueue, so identity and event are committed atomically.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from connector_brain.adapters.models import SupplierProductIdentity
from sa_core.ids import new_ulid
from sa_core.time import utc_now

IdentityState = Literal["new", "changed", "unchanged"]


async def resolve_and_stage(
    session: AsyncSession,
    *,
    supplier_code: str,
    external_id: str,
    content_hash: str,
) -> tuple[str, IdentityState]:
    """Return ``(supplier_product_id, state)`` and stage identity changes in the session.

    - ``new`` — first sight; a fresh ULID is minted and stored.
    - ``changed`` — the content hash differs from last sync; the stored hash is updated.
    - ``unchanged`` — nothing to do.
    """
    row = await session.get(SupplierProductIdentity, (supplier_code, external_id))
    if row is None:
        supplier_product_id = new_ulid()
        session.add(
            SupplierProductIdentity(
                supplier_code=supplier_code,
                external_id=external_id,
                supplier_product_id=supplier_product_id,
                content_hash=content_hash,
            )
        )
        return supplier_product_id, "new"

    if row.content_hash != content_hash:
        row.content_hash = content_hash
        row.updated_at = utc_now()
        return row.supplier_product_id, "changed"

    return row.supplier_product_id, "unchanged"
