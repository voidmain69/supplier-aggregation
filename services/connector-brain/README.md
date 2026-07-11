# connector-brain

Supplier connector for **Brain** (`api.brain.com.ua`). Syncs the Brain catalog, prices and
availability and normalizes them into the platform's canonical DTOs. Implements the
`SupplierConnector` protocol from `sa-connector-sdk`.

All Brain specifics live here (hard rule 8): auth/SID sessions, the 3 req/s rate limit,
pagination, delta discovery, and JSON→DTO normalization. Downstream services only ever see
canonical `RawProduct`/`RawOffer`/`RawCategory`/`RawStock`.

## What it does

- **Auth / sessions** — `POST /auth` (login + MD5 password) → SID, cached per account with
  single-flight re-auth on session expiry (`SessionManager`).
- **Rate limit** — every call goes through a per-account token bucket (`requests_per_second`,
  default 3) so the Brain limit is never exceeded.
- **Raw archive** — each raw response is archived before normalization (hard rule 9); the
  auth response (which carries the SID) is not archived.
- **Reads** — categories, products (cursor pagination over Brain's limit/offset), single
  product by id/articul/code, delta ids (`modified_products`), stocks, and offers
  (price + availability per account).

## Events

Event production via the transactional outbox lands in a follow-up increment (needs the
service DB + Kafka wiring). This increment delivers the connector itself, verified offline.

| Direction | Type | Topic |
|---|---|---|
| out (planned) | `supplier.product.discovered/updated` | `sa.supplier.product` |
| out (planned) | `supplier.offer.price-changed` | `sa.supplier.offer` |

## Configuration

Environment, prefix `CONNECTOR_BRAIN_` (see `settings.py`). No secrets — credentials are
resolved from Vault via each account's `credentials_ref`.

## Run tests

    uv run pytest services/connector-brain

Tests run fully offline against recorded fixtures in `tests/fixtures/brain/` via
`httpx.MockTransport` (no live API). Live smoke tests would be marked `@pytest.mark.live`.
