# search

Finds products for people and agents. Owns a **search index** of products, built from supplier
product events, and serves **lexical** search (free text over name/brand/articul/codes) plus exact
lookups by code, articul and GTIN.

Two processes (separate deployments):
- **API** (`search.main:create_app`) — query endpoints under `/v1`.
- **Consumer** (`python -m search.consumer`) — subscribes to `sa.supplier.product` and indexes
  each discovered product idempotently (dedupe by event id).

## Search model

A document's `search_text` is the lowercased, tokenized bag of its name, brand, articul and
codes. A query is tokenized the same way and **every token must appear** (AND), via portable
`LIKE` matching. On PostgreSQL a `pg_trgm` GIN index keeps this fast (installed by the migration);
SQLite (tests) uses the same query without the index. Exact lookups compare identifiers directly;
GTIN is normalized to GTIN-14 first.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/search` | Lexical search (body: query, cursor, limit); cursor-paginated |
| GET | `/v1/search/by-code/{code}` | Exact match on supplier product code / external id |
| GET | `/v1/search/by-articul/{articul}` | Exact match on articul |
| GET | `/v1/search/by-gtin/{gtin}` | Exact match on GTIN/EAN/UPC (normalized to GTIN-14) |

Errors are `application/problem+json`; every field/param carries an LLM-quality description.

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.product.discovered` | `sa.supplier.product` |

## Configuration

Env prefix `SEARCH_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/search

Unit tests run on SQLite (no Docker); the schema/migrations are also verified on Postgres via
testcontainers (`@pytest.mark.integration`).

## Follow-ups

Semantic (RAG) search over embeddings via the `Embedder` protocol and pgvector (reuses the matching
service's approach); index canonical products from `catalog.product.updated`; hybrid RRF ranking;
PostgreSQL FTS (`tsvector`) ranking; expose through the api-gateway and mcp-gateway.
