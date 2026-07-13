# matching

Owns the **matching decisions** — the mapping from supplier products to canonical products.
It does the deterministic **GTIN auto-link** and **candidate generation + operator curation**
for products without a GTIN (lexical similarity now; semantic pgvector/RAG is a follow-up that
swaps the scorer). It decides *membership* and emits `matching.link.confirmed`; building the
canonical **card** (title/brand/gtin/attributes) belongs to the catalog service
([ADR-0012](../../docs/adr/0012-catalog-owns-canonical.md)). Canonical *reads* are still served
here transitionally (see below).

Two processes (separate deployments):
- **API** (`matching.main:create_app`) — read endpoints under `/v1`.
- **Consumer** (`python -m matching.consumer`) — subscribes to `sa.supplier.product`,
  auto-links products by GTIN, and emits `matching.link.confirmed` via the outbox.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/canonical-products?gtin=` | List canonical products (cursor pagination, GTIN filter) |
| GET | `/v1/canonical-products/{id}` | Fetch one; 404 as RFC 9457 problem+json |
| POST | `/v1/canonical-products/{id}/merge` | Merge one canonical into another (re-links its members) |
| GET | `/v1/curation/queue` | Matches awaiting an operator decision (pending_review) |
| GET | `/v1/curation/stats` | Operator dashboard: pending reviews, canonical count, decisions by action |
| GET | `/v1/curation/decisions` | Append-only decision journal (audit log), cursor-paginated |
| POST | `/v1/curation/links/{spid}/confirm` | Confirm a suggested match (emits link.confirmed) |
| POST | `/v1/curation/links/{spid}/reject` | Reject a suggested match |
| POST | `/v1/curation/links/{spid}/create-new` | Create a new canonical for a product no existing one fits |

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

Swap the candidate scorer from lexical similarity to a real semantic pgvector/RAG model (the
`Embedder` seam is in place); GTIN-collision queue handling; tune thresholds/models on the decision
journal; hand canonical-card *reads* over to catalog via the gateway
([ADR-0012](../../docs/adr/0012-catalog-owns-canonical.md)).
