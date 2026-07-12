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

## Processes

- `python -m connector_brain.sync_consumer` — consumes `sync.job.requested` (from the
  sync-orchestrator) and drives a full account sync (`full_sync.run_account_sync`): fetch
  categories → products → `sync_products`, and offers → `sync_offers`. Staged events go to
  the outbox. **Needs a Vault-backed `CredentialResolver`** (`credentials_ref` → login/
  password) — wire it in `sync_consumer._credential_resolver` before running in production.
- `python -m connector_brain.relay` — ships the outbox to Kafka.

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `sync.job.requested` | `sa.sync.job` |
| out | `supplier.product.discovered` | `sa.supplier.product` |
| out | `supplier.offer.price-changed` | `sa.supplier.offer` |

## Configuration

Environment, prefix `CONNECTOR_BRAIN_` (see `settings.py`). No secrets — credentials are
resolved from Vault via each account's `credentials_ref`.

## Run tests

    uv run pytest services/connector-brain

Tests run fully offline against recorded fixtures in `tests/fixtures/brain/` via
`httpx.MockTransport` (no live API). Live smoke tests would be marked `@pytest.mark.live`.
