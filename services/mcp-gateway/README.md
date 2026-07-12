# mcp-gateway

The platform's **MCP server** for AI agents. Exposes a small, curated set of task-oriented
tools over the internal catalog and offer APIs (read-only HTTP; never their DBs). This is
the single entry point agents use — a task-oriented toolset, not a 1:1 proxy of every
endpoint (see [ADR-0005](../../docs/adr/0005-ai-tools-ready.md)).

## Tools

| Tool | What it does |
|---|---|
| `search_products` | Search/browse supplier products (filter by supplier; cursor-paginated) |
| `get_product` | One supplier product by internal id |
| `get_offers` | All offers (prices per account) for a product |
| `get_best_offer` | Cheapest offer (lowest UAH price) for a product |
| `get_product_with_best_offer` | Product + its cheapest offer in one call (aggregation) |
| `best_offer_for_canonical` | Cheapest offer for a canonical product across ALL suppliers/accounts |

Served over MCP streamable HTTP (`mcp_gateway.main:create_app` → a Starlette app); tool
descriptions come from the function docstrings. `GET /healthz` is available for probes.

## Configuration

Env prefix `MCP_GATEWAY_` (see `settings.py`): `catalog_base_url`, `offer_base_url`.

## Run tests

    uv run pytest services/mcp-gateway

Tool logic is unit-tested against the catalog/offer APIs faked with `httpx.MockTransport`;
a smoke test asserts the MCP server registers every tool with a description and schema.

## Follow-ups

Map REST scopes onto tool auth; add semantic/RAG search and price-history tools as those
services land; generated OpenAPI clients instead of hand-written httpx clients.
