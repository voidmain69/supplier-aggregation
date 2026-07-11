"""Thin HTTP clients for the internal catalog and offer APIs.

The gateway reads from other services over HTTP (never their DB). These wrap the endpoints
the tools need; a 404 becomes ``None`` so tools can report "not found" cleanly. (Generated
OpenAPI clients are a follow-up; httpx is enough for the read paths.)
"""

from __future__ import annotations

from typing import Any

import httpx


class CatalogClient:
    def __init__(self, base_url: str, http: httpx.AsyncClient) -> None:
        self._base = base_url.rstrip("/")
        self._http = http

    async def list_products(
        self, *, supplier: str | None = None, cursor: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if supplier is not None:
            params["supplier"] = supplier
        if cursor is not None:
            params["cursor"] = cursor
        resp = await self._http.get(f"{self._base}/v1/supplier-products", params=params)
        resp.raise_for_status()
        return dict(resp.json())

    async def get_product(self, supplier_product_id: str) -> dict[str, Any] | None:
        resp = await self._http.get(f"{self._base}/v1/supplier-products/{supplier_product_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return dict(resp.json())


class OfferClient:
    def __init__(self, base_url: str, http: httpx.AsyncClient) -> None:
        self._base = base_url.rstrip("/")
        self._http = http

    async def list_offers(
        self, supplier_product_id: str, *, cursor: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"supplier_product_id": supplier_product_id, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        resp = await self._http.get(f"{self._base}/v1/offers", params=params)
        resp.raise_for_status()
        return dict(resp.json())

    async def best_offer(self, supplier_product_id: str) -> dict[str, Any] | None:
        resp = await self._http.get(
            f"{self._base}/v1/offers/best", params={"supplier_product_id": supplier_product_id}
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return dict(resp.json())
