# price-history

Stores **every supplier price change** as a time series and serves an offer's history and
price statistics. In production `price_point` is a TimescaleDB hypertable; on plain
Postgres (tests) it is an ordinary table with identical queries.

Two processes (separate deployments):
- **API** (`price_history.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m price_history.consumer`) — subscribes to `sa.supplier.offer`
  and appends a price point per change (idempotent, dedupe by event id).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/price-history?offer_id=&from=&to=` | Price points over a range (cursor paginated) |
| GET | `/v1/price-history/stats?offer_id=&from=&to=` | min/max/avg/last UAH price + count |

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.offer.price-changed` | `sa.supplier.offer` |

## Configuration

Env prefix `PRICE_HISTORY_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`.

## Run tests

    uv run pytest services/price-history

Unit tests run on SQLite; ingestion + stats are also verified on Postgres via testcontainers
(`@pytest.mark.integration`). The Timescale hypertable is applied only when the extension is
present, so tests use a plain Postgres image.

## Follow-ups

Continuous aggregates (daily min/avg/max) + compression/retention policies; a
`get_price_history` tool in the MCP gateway; Alembic migrations.
