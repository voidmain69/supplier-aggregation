# sync-orchestrator

The **source** of the ingestion pipeline. On a per-account interval it emits
`sync.job.requested` so the owning supplier connector fetches fresh catalog/prices — which
then flow as `supplier.product.discovered` / `supplier.offer.price-changed` through the rest
of the platform. It owns no product data; it only schedules.

Rule 1 (a service never imports another): it hands work to connectors via **events**, not
calls.

## Processes

- `python -m sync_orchestrator.scheduler` — each tick, stages `sync.job.requested` for due
  accounts (interval elapsed since last request) in one transaction.
- `python -m sync_orchestrator.relay` — ships the outbox to Kafka.

## Events

| Direction | Type | Topic |
|---|---|---|
| produces | `sync.job.requested` | `sa.sync.job` |

## Configuration

Env prefix `SYNC_ORCHESTRATOR_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`,
`poll_interval_seconds`, and `accounts` — a JSON list of `{account_id, supplier_code,
credentials_ref, settlement_currency, kind, interval_seconds}`. `credentials_ref` is a Vault
pointer, never a secret.

## Run tests

    uv run pytest services/sync-orchestrator
