# sync-orchestrator

The **source** of the ingestion pipeline. On a per-account interval it emits
`sync.job.requested` so the owning supplier connector fetches fresh catalog/prices — which
then flow as `supplier.product.discovered` / `supplier.offer.price-changed` through the rest
of the platform. It owns no product data; it only schedules.

Rule 1 (a service never imports another): it hands work to connectors via **events**, not
calls.

## Processes

- **API** (`sync_orchestrator.main:create_app`) — read/trigger endpoints under `/v1` for the
  curation-ui sync-monitoring page.
- `python -m sync_orchestrator.scheduler` — each tick, stages `sync.job.requested` for due
  accounts (interval elapsed since last request) in one transaction.
- `python -m sync_orchestrator.relay` — ships the outbox to Kafka.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/sync/accounts` | Per-account sync state: supplier, kind, mode, interval, `last_requested_at`, `next_due_at`, status `never\|ok\|overdue` |
| POST | `/v1/sync/accounts/{account_id}/trigger` | Manual "sync now" — stages `sync.job.requested` immediately |

Operational fields **only** — the API never returns `credentials_ref` or `settlement_currency`
(hard rule 6). Errors are `application/problem+json`.

## Events

| Direction | Type | Topic |
|---|---|---|
| produces | `sync.job.requested` | `sa.sync.job` |

## Configuration

Env prefix `SYNC_ORCHESTRATOR_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`,
`poll_interval_seconds`, and `accounts` — a JSON list of `{account_id, supplier_code,
credentials_ref, settlement_currency, kind, interval_seconds}`, shared by the API and scheduler.
`credentials_ref` is a Vault pointer, never a secret; it and `settlement_currency` stay server-side
and are never exposed by the API.

## Run tests

    uv run pytest services/sync-orchestrator
