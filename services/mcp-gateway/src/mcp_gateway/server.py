"""FastMCP server exposing the curated tools to agents.

Thin wrappers register the tool logic from :mod:`mcp_gateway.tools`; docstrings become the
tool descriptions agents read. Auth/scope mapping (same scopes as the REST APIs) is a
follow-up — see docs/adr/0005-ai-tools-ready.md.
"""

from __future__ import annotations

from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_gateway import tools
from mcp_gateway.clients import CatalogClient, OfferClient, PriceHistoryClient
from mcp_gateway.settings import Settings


def build_server(settings: Settings, *, http: httpx.AsyncClient | None = None) -> FastMCP:
    """Build the MCP server. Inject ``http`` (e.g. a MockTransport client) in tests."""
    client = http or httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    catalog = CatalogClient(settings.catalog_base_url, client)
    offer = OfferClient(settings.offer_base_url, client)
    price_history = PriceHistoryClient(settings.price_history_base_url, client)

    mcp: FastMCP = FastMCP("supplier-aggregation")

    @mcp.tool()
    async def search_products(
        supplier: str | None = None, cursor: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
        """Search or browse supplier products in the catalog. Filter by supplier code
        (e.g. 'brain'); cursor-paginated. Returns items + next_cursor."""
        return await tools.search_products(catalog, supplier=supplier, cursor=cursor, limit=limit)

    @mcp.tool()
    async def get_product(supplier_product_id: str) -> dict[str, Any]:
        """Get one supplier product by its internal supplier_product_id (ULID)."""
        return await tools.get_product(catalog, supplier_product_id)

    @mcp.tool()
    async def get_offers(supplier_product_id: str) -> dict[str, Any]:
        """List all offers (prices per supplier account) for a product."""
        return await tools.get_offers(offer, supplier_product_id)

    @mcp.tool()
    async def get_best_offer(supplier_product_id: str) -> dict[str, Any]:
        """Get the cheapest offer (lowest UAH price) for a product."""
        return await tools.get_best_offer(offer, supplier_product_id)

    @mcp.tool()
    async def get_price_history(
        offer_id: str,
        from_: str | None = None,
        to: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Price history (time series of observed prices) for one offer. Optional ISO-8601 UTC
        `from_`/`to` bounds; cursor-paginated. Use to show or reason about price trends."""
        return await tools.get_price_history(
            price_history, offer_id, from_=from_, to=to, cursor=cursor, limit=limit
        )

    @mcp.tool()
    async def get_offer_price_stats(
        offer_id: str, from_: str | None = None, to: str | None = None
    ) -> dict[str, Any]:
        """Aggregate UAH-price stats (min/max/avg/last/count) for one offer over an optional
        ISO-8601 UTC date range. Use for a quick summary instead of the full history."""
        return await tools.get_offer_price_stats(price_history, offer_id, from_=from_, to=to)

    @mcp.tool()
    async def get_product_with_best_offer(supplier_product_id: str) -> dict[str, Any]:
        """Get a product together with its cheapest offer in a single call."""
        return await tools.get_product_with_best_offer(catalog, offer, supplier_product_id)

    @mcp.tool()
    async def best_offer_for_canonical(canonical_product_id: str) -> dict[str, Any]:
        """Cheapest offer for a canonical product across ALL suppliers and accounts.
        Use this when you have a canonical product and want the best price anywhere."""
        return await tools.best_offer_for_canonical(catalog, offer, canonical_product_id)

    return mcp
