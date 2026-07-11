"""BrainConnector — the SupplierConnector implementation for Brain.

Wires the low-level :class:`BrainClient` to the pure normalizers, exposing the canonical
read interface. One connector instance is bound to one supplier account (Brain requires a
per-account SID for every call, including catalog reads).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from connector_brain.adapters.brain_client import BrainApiError, BrainClient
from connector_brain.domain import normalize
from connector_brain.settings import Settings
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
from sa_core.pagination import Page, decode_cursor, encode_cursor

_BRAIN_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class BrainConnector:
    """Read-only Brain integration bound to a single account."""

    supplier_code = "brain"

    def __init__(self, *, client: BrainClient, account: AccountCtx, settings: Settings) -> None:
        self._client = client
        self._account = account
        self._settings = settings

    async def healthcheck(self) -> ConnectorHealth:
        try:
            await self._client.get_stocks()
        except BrainApiError as exc:
            return ConnectorHealth(ok=False, detail=str(exc))
        return ConnectorHealth(ok=True)

    async def fetch_categories(self) -> AsyncIterator[RawCategory]:
        for row in await self._client.get_categories():
            yield normalize.normalize_category(row)

    async def fetch_products(self, category_id: str, cursor: str | None) -> Page[RawProduct]:
        offset = int(decode_cursor(cursor)["offset"]) if cursor else 0
        limit = self._settings.page_size
        rows = await self._client.get_products(category_id, limit=limit, offset=offset)
        next_cursor = encode_cursor({"offset": offset + limit}) if len(rows) == limit else None
        return Page(items=[normalize.normalize_product(r) for r in rows], next_cursor=next_cursor)

    async def fetch_product(self, ref: ProductRef) -> RawProduct:
        if ref.external_id is not None:
            raw = await self._client.get_product_by_id(ref.external_id)
        elif ref.articul is not None:
            raw = await self._client.get_product_by_articul(ref.articul)
        elif ref.product_code is not None:
            raw = await self._client.get_product_by_code(ref.product_code)
        else:  # unreachable: ProductRef validates exactly one identifier
            raise ValueError("ProductRef has no identifier")
        return normalize.normalize_product(raw)

    async def fetch_deltas(self, since: datetime) -> AsyncIterator[DeltaRef]:
        modified_time = since.strftime(_BRAIN_DATETIME_FMT)
        offset = 0
        limit = self._settings.page_size
        while True:
            ids = await self._client.get_modified_products(
                modified_time=modified_time, limit=limit, offset=offset
            )
            for external_id in ids:
                yield DeltaRef(external_id=str(external_id))
            if len(ids) < limit:
                return
            offset += limit

    async def fetch_offers(self, account: AccountCtx) -> AsyncIterator[RawOffer]:
        currency = account.settlement_currency
        for category in await self._client.get_categories():
            category_id = str(category["categoryID"])
            offset = 0
            limit = self._settings.page_size
            while True:
                rows = await self._client.get_products(category_id, limit=limit, offset=offset)
                for row in rows:
                    try:
                        yield normalize.normalize_offer(row, settlement_currency=currency)
                    except ValueError:
                        continue  # product without a usable price -> no offer
                if len(rows) < limit:
                    break
                offset += limit

    async def fetch_stocks(self, account: AccountCtx) -> list[RawStock]:
        return [normalize.normalize_stock(row) for row in await self._client.get_stocks()]
