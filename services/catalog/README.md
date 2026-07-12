# catalog

Owns the platform's view of **supplier products**: ingests them from connector events and
serves them via an AI-ready read API. The canonical catalog + matching build on this later.

Two processes (separate deployments):
- **API** (`catalog.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m catalog.consumer`) — subscribes to `sa.supplier.product`
  (upsert products) and `sa.matching.link` (record each product's canonical mapping),
  both idempotent.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/supplier-products` | List supplier products (cursor pagination, `supplier` filter) |
| GET | `/v1/supplier-products/{supplier_product_id}` | Fetch one; 404 as RFC 9457 problem+json |

Errors are `application/problem+json`; every field/param carries an LLM-quality description.

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.product.discovered` | `sa.supplier.product` |
| in | `matching.link.confirmed` | `sa.matching.link` |

## Configuration

Env prefix `CATALOG_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/catalog

Unit tests run on SQLite (no Docker); ingestion is also verified end-to-end on Postgres via
testcontainers (`@pytest.mark.integration`).

## Follow-ups

Export `openapi.json` + spectral AI-ready lint + populate `tool_manifest.json`; canonical
products and matching; Alembic migrations.
