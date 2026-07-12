# offer

Owns **supplier offers** — a price for a product under a supplier account — and each account's
**financial terms**. Ingests offers from connector price events, folds the account's terms into a
comparable **effective UAH price** (pricing engine), and serves them via an AI-ready API.

Two processes (separate deployments):
- **API** (`offer.main:create_app`) — read endpoints under `/v1` + an admin terms endpoint.
- **Consumer** (`python -m offer.consumer`) — subscribes to `sa.supplier.offer` and upserts
  offers idempotently (dedupe by event id).

## Effective price

`effective_price_uah = base_price → UAH (currency / account FX) × (1 − discount) × (1 + markup)`.
The base UAH conversion uses the account's `fx_rate_to_uah`, or the supplier-provided `price_uah`
when no rate is set, or the base price directly for UAH accounts; it is null when a non-UAH offer
has no usable rate. Offers are ranked by this value. Account financial terms are sensitive
(hard rule 6): set them via the admin endpoint, never returned by read endpoints.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/offers?supplier_product_id=` | List offers for a product (cursor pagination) |
| GET | `/v1/offers/best?supplier_product_id=` | Cheapest offer by effective UAH price; 404 if none priced |
| GET | `/v1/offers/{offer_id}` | Fetch one; 404 as RFC 9457 problem+json |
| PUT | `/v1/accounts/{id}/terms` | Set an account's financial terms + re-price its offers (admin, scope `offer:admin`) |

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

Emit `offer.effective-price-changed` via the outbox when the effective price moves (for
price-history); stock/availability views; best-offer filters (qty, max delivery days).
