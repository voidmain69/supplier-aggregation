# matching

Owns the **canonical catalog** and the mapping from supplier products to canonical
products. This slice does the deterministic **GTIN auto-link**; RAG candidates + operator
curation are a follow-up.

Two processes (separate deployments):
- **API** (`matching.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m matching.consumer`) — subscribes to `sa.supplier.product`,
  auto-links products by GTIN, and emits `matching.link.confirmed` via the outbox.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/canonical-products?gtin=` | List canonical products (cursor pagination, GTIN filter) |
| GET | `/v1/canonical-products/{id}` | Fetch one; 404 as RFC 9457 problem+json |

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.product.discovered` | `sa.supplier.product` |
| out | `matching.link.confirmed` | `sa.matching.link` |

## Configuration

Env prefix `MATCHING_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/matching

Unit tests run on SQLite; the auto-link + emit loop is verified end-to-end on Postgres via
testcontainers (`@pytest.mark.integration`).

## Follow-ups

RAG candidate generation + operator curation queue; GTIN collision handling; attach
canonical_product_id back onto catalog products; Alembic migrations.
