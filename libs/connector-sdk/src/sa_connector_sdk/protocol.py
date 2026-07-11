"""The SupplierConnector protocol.

Every connector implements this interface; core services depend only on it, never on a
concrete connector. Read methods only — ordering, reservations and shipping are out of
scope for the aggregation platform.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from sa_connector_sdk.dto import (
    AccountCtx,
    ConnectorHealth,
    DeltaRef,
    ProductRef,
    RawCategory,
    RawOffer,
    RawProduct,
    RawStock,
)
from sa_core.pagination import Page


@runtime_checkable
class SupplierConnector(Protocol):
    """Read-only integration with one supplier's product/pricing API."""

    supplier_code: str

    async def healthcheck(self) -> ConnectorHealth:
        """Verify auth and connectivity without mutating anything."""
        ...

    def fetch_categories(self) -> AsyncIterator[RawCategory]:
        """Stream the supplier's category tree."""
        ...

    async def fetch_products(self, category_id: str, cursor: str | None) -> Page[RawProduct]:
        """Fetch one page of products in a category; use the returned cursor for the next."""
        ...

    async def fetch_product(self, ref: ProductRef) -> RawProduct:
        """Fetch a single product by id, articul, or product code."""
        ...

    def fetch_deltas(self, since: datetime) -> AsyncIterator[DeltaRef]:
        """Stream ids of products changed since a timestamp (for incremental sync)."""
        ...

    def fetch_offers(self, account: AccountCtx) -> AsyncIterator[RawOffer]:
        """Stream current prices and availability for an account."""
        ...

    async def fetch_stocks(self, account: AccountCtx) -> list[RawStock]:
        """List the supplier's stock locations (self-describing availability)."""
        ...
