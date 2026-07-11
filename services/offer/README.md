# offer

Owns **supplier offers** — a price for a product under a supplier account. Ingests them
from connector price events and serves them via an AI-ready API.

Two processes (separate deployments):
- **API** (`offer.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m offer.consumer`) — subscribes to `sa.supplier.offer` and upserts
  offers idempotently (dedupe by event id).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/offers?supplier_product_id=` | List offers for a product (cursor pagination) |
| GET | `/v1/offers/best?supplier_product_id=` | Cheapest offer (lowest UAH price); 404 if none priced |
| GET | `/v1/offers/{offer_id}` | Fetch one; 404 as RFC 9457 problem+json |

Errors are `application/problem+json`; every field/param carries an LLM-quality description.

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.offer.price-changed` | `sa.supplier.offer` |

## Configuration

Env prefix `OFFER_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/offer

Unit tests run on SQLite (no Docker); ingestion is also verified end-to-end on Postgres via
testcontainers (`@pytest.mark.integration`).

## Follow-ups

Effective price from account financial terms (currently the base price is served); stock/
availability views; Alembic migrations.
