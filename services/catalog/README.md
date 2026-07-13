# catalog

Owns the platform's view of **supplier products** and the **canonical product card**. Ingests
supplier products from connector events, and — on matching's decisions — rebuilds the canonical
card and publishes it as the single source of truth for downstream services
([ADR-0012](../../docs/adr/0012-catalog-owns-canonical.md)).

Two processes (separate deployments):
- **API** (`catalog.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m catalog.consumer`) — subscribes to `sa.supplier.product` (upsert
  products) and `sa.matching.link` (`matching.link.confirmed` → link the supplier product to its
  canonical, deterministically **rebuild the card** via `build_canonical_card`, and emit
  `catalog.product.updated`; on merge/split the previous canonical is rebuilt too). Idempotent.
- **Relay** (`python -m catalog.relay`) — ships the outbox to Kafka.

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
| out | `catalog.product.updated` | `sa.catalog.product` |

## Configuration

Env prefix `CATALOG_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/catalog

Unit tests run on SQLite (no Docker); ingestion is also verified end-to-end on Postgres via
testcontainers (`@pytest.mark.integration`).

## Follow-ups

Serve canonical **card reads** from here (`GET /v1/canonical-products`), taking over from matching
via the gateway (see [ADR-0012](../../docs/adr/0012-catalog-owns-canonical.md)); category taxonomy +
supplier→canonical category mapping (a separate greenfield epic).
