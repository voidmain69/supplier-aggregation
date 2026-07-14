from __future__ import annotations

import httpx
from mcp_gateway.server import build_server
from mcp_gateway.settings import Settings

_EXPECTED_TOOLS = {
    "search_products",
    "get_product",
    "get_offers",
    "get_best_offer",
    "get_price_history",
    "get_offer_price_stats",
    "get_product_with_best_offer",
    "best_offer_for_canonical",
    "find_products",
    "find_canonical_products",
    "get_price_daily",
    "best_price_for_query",
}


async def test_server__registers_all_tools() -> None:
    server = build_server(Settings(), http=httpx.AsyncClient())
    tools = await server.list_tools()
    assert {t.name for t in tools} == _EXPECTED_TOOLS


async def test_server__tools_have_descriptions_and_schemas() -> None:
    server = build_server(Settings(), http=httpx.AsyncClient())
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description  # docstrings surface to agents
        assert tool.inputSchema["type"] == "object"
    by_name = {t.name: t for t in tools}
    assert "supplier_product_id" in by_name["get_best_offer"].inputSchema["properties"]
